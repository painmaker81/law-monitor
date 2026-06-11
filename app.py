import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import urllib3

# 사내망 보안 경고 완전히 끄기
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="법규 이력 시점 조회", layout="wide")
st.title("📌 안전·환경 규제 시점별 이력 모니터링")

API_KEY = "gapjin"

base_laws = [
    "산업안전보건법", "중대재해 처벌 등에 관한 법률", "산업재해보상보험법",
    "소방시설 설치 및 관리에 관한 법률", "폐기물관리법", "화학물질관리법",
    "대기환경보전법", "소음·진동관리법", "감염병의 예방 및 관리에 관한 법률",
    "악취방지법", "물환경보전법", "순환경제사회 전환 촉진법",
    "위험물안전관리법", "근로기준법", "도시가스사업법"
]

law_list = []
for law in base_laws:
    law_list.append({"name": law, "type": "법"})
    law_list.append({"name": law, "type": "시행령"})
    law_list.append({"name": law, "type": "시행규칙"})
law_list.append({"name": "산업안전보건기준에 관한 규칙", "type": "단독규칙"})

selected_date = st.date_input("조회 기준일을 선택하세요", datetime(2026, 2, 28))
target_date_str = selected_date.strftime("%Y-%m-%d")

# 윈도우/보안 장비 회피형 통신 함수
def get_xml_data(url):
    try:
        # User-Agent를 브라우저처럼 위장
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        # verify=False로 사내망 SSL/인증서 충돌 방지
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        if response.status_code == 200:
            return ET.fromstring(response.content)
    except Exception:
        return None
    return None

@st.cache_data(ttl=3600)
def fetch_law_history(law_name, doc_type, target_date):
    query = law_name if doc_type in ["법", "단독규칙"] else f"{law_name} {doc_type}"
    search_url = f"https://www.law.go.kr/DRF/lawSearch.do?OC={API_KEY}&target=law&type=XML&query={query}"
    
    root = get_xml_data(search_url)
    if root is None: return "연결 실패"
    
    lsi_seq = root.findtext(".//law/법령일련번호")
    if not lsi_seq: return "일련번호 없음"
    
    hist_url = f"https://www.law.go.kr/DRF/lawService.do?OC={API_KEY}&target=history&LID={lsi_seq}"
    hist_root = get_xml_data(hist_url)
    if hist_root is None: return "연혁 없음"
    
    histories = []
    for hist in hist_root.findall(".//history"):
        eff_date = hist.findtext("시행일자")
        if eff_date:
            histories.append({
                "pub_date": hist.findtext("공포일자"),
                "eff_date": eff_date,
                "pub_num": hist.findtext("공포번호"),
                "change_type": hist.findtext("제개정구분")
            })
    
    target_dt = datetime.strptime(target_date, "%Y-%m-%d")
    valid = [h for h in histories if datetime.strptime(h["eff_date"], "%Y%m%d") <= target_dt]
    if not valid: return "기준일 데이터 없음"
    
    latest = sorted(valid, key=lambda x: x["eff_date"], reverse=True)[0]
    return {
        "법규명": law_name, "구분": doc_type,
        "공포번호": f"제{latest['pub_num']}호",
        "개정일자": latest['pub_date'],
        "시행일자": latest['eff_date'],
        "비고": latest['change_type']
    }

if st.button("조회 시작", type="primary"):
    results = []
    with st.spinner("서버와 동기화 중..."):
        for item in law_list:
            res = fetch_law_history(item["name"], item["type"], target_date_str)
            if isinstance(res, dict): results.append(res)
    
    if results:
        st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
    else:
        st.error("데이터 조회 실패. 회사 인터넷 환경에서 API 접근이 차단되었을 수 있습니다.")