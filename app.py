import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 설정된 API KEY 호출
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

selected_date = st.date_input("조회 기준일을 선택하세요", datetime(2026, 2, 28))
target_date_val = int(selected_date.strftime("%Y%m%d"))

def get_xml_data(url):
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, verify=False, timeout=15)
        if response.status_code == 200: return ET.fromstring(response.content)
    except: return None
    return None

@st.cache_data(ttl=3600)
def fetch_law_history(law_name, doc_type, target_val):
    query = f"{law_name} {doc_type}"
    search_url = f"https://www.law.go.kr/DRF/lawSearch.do?OC={API_KEY}&target=law&type=XML&query={quote(query)}"
    
    root = get_xml_data(search_url)
    if root is None: return None
    
    lsi_seq = root.findtext(".//law/법령일련번호")
    if not lsi_seq: return None
    
    hist_url = f"https://www.law.go.kr/DRF/lawService.do?OC={API_KEY}&target=history&LID={lsi_seq}"
    hist_root = get_xml_data(hist_url)
    if hist_root is None: return None
    
    # 데이터 파싱 및 날짜 비교 (가장 중요)
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
        "법규명": law_name, "구분": doc_type, 
        "공포번호": f"제{latest['pub_num']}호", 
        "시행일자": latest['eff_date'],
        "구분비고": latest['change_type']
    }

if st.button("조회 시작"):
    results = []
    with st.spinner("법령 데이터를 수집 중입니다..."):
        for item in law_list:
            res = fetch_law_history(item["name"], item["type"], target_date_val)
            if res: results.append(res)
    
    if results:
        st.dataframe(pd.DataFrame(results), use_container_width=True)
    else:
        st.error("데이터를 불러오지 못했거나, 해당 날짜 이전의 연혁이 없습니다.")
