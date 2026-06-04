# Research Notes

## What A Good Policy Information Site Should Do

Insurance product information should be summarized into consumer-readable checkpoints, with original policy documents kept as source evidence. The site should show coverage, definitions, exclusions, conditions, premium/renewal facts, and source status before asking readers to open a PDF.

## Source-Backed Design Principles

- Taiwan's Insurance Institute product database is intended for the public to query detailed insurance product information, not just a generic document list: <https://insprod.tii.org.tw/Default.aspx>.
- FSC investment-type insurance disclosure rules require important policy summaries to include items such as suspension/reinstatement conditions, non-covered matters, loan interest, fee structure, conversion, dividends, and surrender fees: <https://law.fsc.gov.tw/EngLawContent.aspx?id=1544&lan=C>.
- FSC inspection guidance flags consumer harm when warnings and important matters are not clearly disclosed, including disease waiting periods, risk warnings, fees, and claim dispute responses that fail to cite policy clauses: <https://law.fsc.gov.tw/LawContent.aspx?id=GL001865>.
- Life insurance claim handling guidance lists common review points: valid policy, complete claim documents, whether the accident occurred during the policy period, whether the claimed item matches coverage, exclusions, waiting periods, definitions, and claim amount: <https://law.lia-roc.org.tw/Law/Content?lsid=FL040403>.
- California DOI explains that coverage documents should help consumers understand what is covered, what is excluded, what costs apply, and how benefits are computed: <https://www.insurance.ca.gov/01-consumers/110-health/30-have/understand-policy.cfm>.
- South Carolina DOI describes common insurance contract parts: declarations, insuring agreement, exclusions, and conditions: <https://doi.sc.gov/957/Understanding-Your-Insurance-Policy>.
- NAIC consumer guidance highlights the importance of terminology, insuring agreements, covered perils, exclusions, and declaration/information pages: <https://content.naic.org/article/consumer-insight-understanding-your-homeowners-or-renters-policy>.

## 2026-06-04 Reader-First UI Update

The current UI should lead with policy-level quick-read cards, not source lists. This is based on:

- FSC consumer guidance says many insurance disputes come from not reading policy terms carefully, and highlights product nature, coverage / benefit items, exclusions, and source terms as first things consumers should understand: <https://www.fsc.gov.tw/ch/home.jsp?dataserno=201802140002&dtable=News&id=96&mcustomize=news_view.jsp&parentpath=0%2C2&toolsflag=Y>.
- FSC health-insurance guidance specifically calls out product type, disease / medical definitions, waiting periods, exclusions, benefit caps, and truthful health disclosure as important consumer review points: <https://www.fsc.gov.tw/ch/home.jsp?dataserno=202503060002&dtable=News&id=96&mcustomize=news_view.jsp&parentpath=0%2C2>.
- FSC law guidance says coverage scope or definitions that differ from ordinary consumer understanding should be disclosed because they can cause claim disputes: <https://law.fsc.gov.tw/LawContent.aspx?id=FE061026>.
- NN/g reading research says web users scan pages and benefit from meaningful headings, grouped content, bullets, and important words placed early: <https://www.nngroup.com/articles/how-users-read-on-the-web/> and <https://www.nngroup.com/articles/f-shaped-pattern-reading-web-content/>.
- web.dev CLS guidance treats unexpected layout shift as distracting and frustrating, so search/filter changes should reserve stable space and avoid forced scroll jumps: <https://web.dev/articles/optimize-cls>.
- MODA's 2025 Digital Access Survey reports high internet access and common product/service information search and online reading in Taiwan, supporting a mobile-readable, scan-first interface: <https://moda.gov.tw/en/press/press-releases/18674>.

UI consequence:

- Each policy card always has four fixed reader sections: `保障項目`, `重要定義`, `特殊項目`, and `理賠申請`.
- Each section shows status, a short derived summary, matched terms, and page hints.
- Search targets the policy text evidence and focus-card terms, not only company names or URLs.
- Source lists remain available, but they are secondary evidence below the policy cards.
- The search form does not call `scrollIntoView`; card grids use stable columns and responsive constraints to reduce visual jumping.

## Field Priority

1. Coverage and claim benefits.
2. Definitions that decide whether the benefit applies.
3. Waiting period, elimination period, and effective date.
4. Exclusions and non-covered matters.
5. Premium, fees, renewal, lapse, reinstatement, and surrender.
6. Underwriting limits, age, occupation, health declaration, and riders.
7. Original source, version, status, and verification date.

## Wording Boundary

Use:

- `依原始條款記載`
- `需以保險公司審核與正式條款為準`
- `摘要欄位，請回到官方文件確認`

Avoid:

- `一定理賠`
- `保證給付`
- `符合即可領`
- `最適合你`
- `官方認定`
