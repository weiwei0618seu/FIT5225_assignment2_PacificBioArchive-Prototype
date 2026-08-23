# Team Report Draft

`Pacific_BioArchive_Team_Report_DRAFT.docx` is a four-page, 766-word editable
draft using Arial 12 pt, a three-column contribution table, simple user guide,
explicit Generative AI declaration, and an AWS-only architecture figure built
from the official AWS Architecture Icons package dated 31 July 2026.

It is deliberately not submission-ready until the team replaces:

- four member name/student-ID placeholders;
- the two live UI screenshot panels;
- any provisional AWS wording with completed Stage 6.3 evidence.

The private official repository link is already included. Contribution values
are provisionally 25% each and must be confirmed truthfully; no person may
exceed 30%.

## QA performed

- Microsoft Word PDF render: four pages visually inspected at 144 DPI;
- no clipping, overlap, split table rows, broken headers/footers or unreadable
  icon labels observed;
- accessibility audit: zero high/medium/low findings;
- contribution table geometry: 9360 DXA total, 120 DXA indent, matching grid and
  cell widths on every row;
- Word total word count including placeholders/table: 766, below the 1,000-word
  ceiling even before the permitted table/figure/screenshot/reference exclusions;
- DOCX SHA-256:
  `3E651108DB84BF64DFA4BD920EA8B91BD6128983DC9525F6DC20D70F8A2C545F`;
- diagram SHA-256:
  `988D9C0782833F7A5B84EA6FE7901DD6A718F16FB5E45544B6ECC0D3E6DA69D2`.

The current diagram is `aws_architecture_diagram-v2.png`. It preserves the
official icon set while removing the account identifier and accurately labels
CloudWatch as logs/diagnostics rather than claiming an uncreated Alarm resource.

The packaged LibreOffice renderer was attempted first but `soffice` is not
installed on this workstation. Word's headless PDF export plus page PNG review
was used as the documented visual-QA fallback. Export the completed report to
PDF only after all placeholders and live evidence are resolved.
