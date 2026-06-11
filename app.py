import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
from datetime import datetime
import urllib3

# 보안 경고 방지
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Streamlit Cloud의 Secrets에서 API 키 호출
# 설정된 이름표 'gapjin'에 'gapjin7237'이라는 키값이 저장되어 있어야 합니다.
API_KEY = st.secrets["gapjin"]

st.set_page_config(page_title="법규 이력 시점 조회", layout="wide")
st.title("📌 갑진기업 안전·환경 규제 시점별 이력 모니터링")

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
target_date_str = selected_date.strftime("%Y-%m-%d")

def get_xml_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, verify=False, timeout=15)
        if response.status_code == 200:
            return ET.fromstring(response.content)
    except:
        return None
    return None

@st.cache_data(ttl=3600)
def fetch_law_history(law_name, doc_type, target_date):
    query = law_name if doc_type in ["법", "단독규칙"] else f"{law_name} {doc_type}"
    # API 호출 시 API_KEY 변수를 직접 연결
    search_url = f"https://www.law.go.kr/DRF/lawSearch.do?OC={API_KEY}&target=law&type=XML&query={quote(query)}"
    
    root = get_xml_data(search_url)
    if root is None: return None
    
    lsi_seq = root.findtext(".//law/법령일련번호")
    if not lsi_seq: return None
    
    hist_url = f"https://www.law.go.kr/DRF/lawService.do?OC={API_KEY}&target=history&LID={lsi_seq}"
    hist_root = get_xml_data(hist_url)
    if hist_root is None: return None
    
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
    if not valid: return None
    
    latest = sorted(valid, key=lambda x: x["eff_date"], reverse=True)[0]
    return {
        "법규명": law_name, "구분": doc_type,
        "공포번호": f"제{latest['pub_num']}호",
        "개정일자": latest['pub_date'],
        "시행일자": latest['eff_date'],
        "비고": latest['change_type'],
        "상세보기": f"https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq={lsi_seq}&viewCls=lsRvsDocInfoP"
    }

if st.button("조회 시작", type="primary"):
    results = []
    with st.spinner("법제처 서버와 동기화 중입니다..."):
        for item in law_list:
            res = fetch_law_history(item["name"], item["type"], target_date_str)
            if res: results.append(res)
    
    if results:
        st.success(f"{len(results)}개의 법규 데이터를 성공적으로 불러왔습니다!")
        st.dataframe(pd.DataFrame(results), column_config={"상세보기": st.column_config.LinkColumn("원문")}, use_container_width=True, hide_index=True)
    else:
        st.error("데이터를 불러오지 못했습니다. API KEY 승인 대기 중이거나 서버 응답이 없습니다.")
