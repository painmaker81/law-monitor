import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
from datetime import datetime

# Streamlit Cloud의 Secrets에서 API 키 호출
API_KEY = st.secrets["gapjin"]

st.set_page_config(page_title="법규 이력 시점 조회", layout="wide")
st.title("📌 갑진기업 안전·환경 규제 시점별 이력 모니터링")

# 모니터링 대상 15개 핵심 법령 리스트
base_laws = [
    "산업안전보건법", "중대재해 처벌 등에 관한 법률", "산업재해보상보험법",
    "소방시설 설치 및 관리에 관한 법률", "폐기물관리법", "화학물질관리법",
    "대기환경보전법", "소음·진동관리법", "감염병의 예방 및 관리에 관한 법률",
    "악취방지법", "물환경보전법", "순환경제사회 전환 촉진법",
    "위험물안전관리법", "근로기준법", "도시가스사업법"
]

law_list = [{"name": law, "type": t} for law in base_laws for t in ["법", "시행령", "시행규칙"]]
law_list.append({"name": "산업안전보건기준에 관한 규칙", "type": "단독규칙"})

selected_date = st.date_input("조회 기준일을 선택하세요", datetime(2026, 2, 28))
target_date_val = int(selected_date.strftime("%Y%m%d"))

# 법제처 공식 규격 맞춤형 데이터 요청 함수
def get_law_xml(url):
    try:
        # 공식 가이드대로 User-Agent나 verify=False 없이 순수하게 요청
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return ET.fromstring(response.content)
    except:
        return None
    return None

@st.cache_data(ttl=3600)
def fetch_law_history(law_name, doc_type, target_val):
    query = law_name if doc_type in ["법", "단독규칙"] else f"{law_name} {doc_type}"
    
    # 1. 법령일련번호 검색 (공식 가이드 주소 구조 적용)
    search_url = f"https://www.law.go.kr/DRF/lawSearch.do?OC={API_KEY}&target=law&type=XML&query={quote(query)}"
    root = get_law_xml(search_url)
    if root is None: return None
    
    lsi_seq = root.findtext(".//law/법령일련번호")
    if not lsi_seq: return None
    
    # 2. 해당 일련번호의 연혁 이력 검색
    hist_url = f"https://www.law.go.kr/DRF/lawService.do?OC={API_KEY}&target=history&LID={lsi_seq}"
    hist_root = get_law_xml(hist_url)
    if hist_root is None: return None
    
    # 선택한 기준일 시점의 최신 제개정 데이터 매칭
    latest = None
    for hist in hist_root.findall(".//history"):
        eff_date_str = hist.findtext("시행일자")
        if eff_date_str:
            eff_date_int = int(eff_date_str)
            if eff_date_int <= target_val:
                if latest is None or eff_date_int > int(latest['eff_date']):
                    latest = {
                        "pub_num": hist.findtext("공포번호"),
                        "eff_date": eff_date_str,
                        "change_type": hist.findtext("제개정구분")
                    }
    
    if not latest: return None
    return {
        "법규명": law_name, 
        "구분": doc_type, 
        "공포번호": f"제{latest['pub_num']}호", 
        "시행일자": datetime.strptime(latest['eff_date'], "%Y%m%d").strftime("%Y-%m-%d"),
        "제개정구분": latest['change_type'],
        "원문보기": f"https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq={lsi_seq}"
    }

# 조회 버튼 클릭 시 가동
if st.button("조회 시작", type="primary"):
    results = []
    with st.spinner("법제처 표준 API 프로토콜로 실시간 동기화 중..."):
        for item in law_list:
            res = fetch_law_history(item["name"], item["type"], target_date_val)
            if res: results.append(res)
    
    if results:
        st.success(f"총 {len(results)}개의 핵심 안전·환경 법령 이력을 로드했습니다.")
        df = pd.DataFrame(results)
        st.dataframe(
            df, 
            column_config={"원문보기": st.column_config.LinkColumn("링크")}, 
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.error("법제처 API 서버 응답이 없습니다. 오픈 API 신청 상태(도메인 주소 허용 등)를 다시 확인해 주세요.")
