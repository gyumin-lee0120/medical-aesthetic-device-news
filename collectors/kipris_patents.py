"""KIPRIS Plus 특허 출원 트렌드 연동 훅.
실제 호출은 KIPRIS Plus에서 발급한 API 서비스/키가 필요합니다.
키/서비스 명세가 준비되기 전에는 데이터를 만들지 않아, 추정값을 표시하지 않습니다.
"""
import json, os, sys
from pathlib import Path
import yaml

BASE=Path(__file__).resolve().parents[1]
CFG=yaml.safe_load((BASE/"config.yaml").read_text(encoding="utf-8"))
OUTS=[BASE/"data"/"patent_trend.json", BASE/"docs"/"data"/"patent_trend.json"]

def run():
    src=CFG.get("sources",{}).get("kipris_patents",{})
    if not src.get("enabled",False):
        print("kipris_patents 비활성화 — KIPRIS Plus API 키 발급 후 활성화하세요.")
        return
    key=os.environ.get("KIPRIS_API_KEY")
    if not key:
        print("[오류] KIPRIS_API_KEY가 없습니다.", file=sys.stderr); sys.exit(1)
    # KIPRIS Plus는 선택한 API 상품별 endpoint/파라미터가 달라
    # 서비스 신청 후 받은 명세서 기준으로 구현해야 합니다.
    print("[대기] KIPRIS Plus 서비스 명세 연결이 필요합니다. 가짜/추정 데이터를 저장하지 않습니다.")
    sys.exit(2)

if __name__=="__main__":
    run()
