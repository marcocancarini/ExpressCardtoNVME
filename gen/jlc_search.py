"""Cerca componenti nel catalogo JLCPCB/LCSC. Uso: jlc_search.py "keyword" [n]"""
import json, sys, urllib.request
def search(kw, n=6):
    req = urllib.request.Request("https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList",
        data=json.dumps({"keyword": kw, "currentPage": 1, "pageSize": n}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    return (d.get("data") or {}).get("componentPageInfo", {}).get("list") or []
if __name__ == "__main__":
    for kw in sys.argv[1:]:
        print("##", kw)
        for c in search(kw):
            print(f"  {c['componentCode']:>9} {c.get('componentLibraryType','')[:6]:6} stk={c.get('stockCount')!s:>7} {c.get('componentModelEn','')[:28]:28} {c.get('componentSpecificationEn','')[:16]:16} {(c.get('describe') or '')[:70]}")
