import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
API_KEY = st.secrets["gapjin"]

st.set_page_config(layout="wide")
st.title("📌 갑진기업 안전·환경 규제 조회")

# 테스트 법령 리스트 (확실하게 데이터가 있는 것들로만 구성)
base_laws = ["산업안전보건법", "폐기물관리법"]
law_list = [{"name": law, "type": "법"} for law in base_laws]

@st.cache_data(ttl=3600)
def fetch_raw_data(law_name):
    # 연혁을 거치지 않고 바로 검색 API에서 정보를 가져옵니다
    search_url = f"https://www.law.go.kr/DRF/lawSearch.do?OC={API_KEY}&target=law&type=XML&query={quote(law_name)}"
    root = requests.get(search_url, verify=False).content
    root = ET.fromstring(root)
    
    # XML에서 법령명과 시행일자를 무조건 추출
    law_info = root.find(".//law")
    if law_info is not None:
        return {
            "법규명": law_info.findtext("법령명한글"),
            "시행일자": law_info.findtext("시행일자"),
            "공포번호": law_info.findtext("공포번호"),
            "원문링크": f"https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq={law_info.findtext('법령일련번호')}"
        }
    return None

if st.button("강제 조회 시작"):
    results = []
    for item in law_list:
        res = fetch_raw_data(item["name"])
        if res: results.append(res)
    
    if results:
        st.dataframe(pd.DataFrame(results), use_container_width=True)
    else:
        st.error("데이터를 찾을 수 없습니다. API 키 상태와 서버 연결을 확인하세요.")
