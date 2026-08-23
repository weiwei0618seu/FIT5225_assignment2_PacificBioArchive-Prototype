# Team Report Draft

`Pacific_BioArchive_Team_Report_DRAFT.docx` is a five-page, 778-word editable
draft using Arial 12 pt, a three-column contribution table, simple user guide,
explicit Generative AI declaration, two sanitized live UI figures, and an
AWS-only architecture figure built from the official AWS Architecture Icons
package dated 31 July 2026.

It is deliberately not submission-ready until the team replaces:

- four member name/student-ID placeholders;
- the provisional 25% contribution split, if the team agrees on a different
  truthful distribution within the 30% per-person limit.

The private official repository link is already included. Contribution values
are provisionally 25% each and must be confirmed truthfully; no person may
exceed 30%.

## QA performed

- the packaged `render_docx.py` workflow was attempted but this workstation has
  no LibreOffice/`soffice`; the documented Microsoft Word PDF fallback produced
  five pages that were all visually inspected at 144 DPI;
- no clipping, overlap, split table rows, broken headers/footers or unreadable
  icon labels observed;
- accessibility audit: zero high/medium/low findings;
- image audit: three inline figures and no high-risk floating anchors;
- contribution table geometry: 9360 DXA total, 120 DXA indent, matching grid and
  cell widths on every row;
- Word total word count including placeholders/table: 778, below the 1,000-word
  ceiling even before the permitted table/figure/screenshot/reference exclusions;
- DOCX SHA-256:
  `8B70FD70C2941FC8D1E73EA6F2E136BC68E2B33843A8A83F864557E530262D60`;
- diagram SHA-256:
  `988D9C0782833F7A5B84EA6FE7901DD6A718F16FB5E45544B6ECC0D3E6DA69D2`.

The current diagram is `aws_architecture_diagram-v2.png`. It preserves the
official icon set while removing the account identifier and accurately labels
CloudWatch as logs/diagnostics rather than claiming an uncreated Alarm resource.

Export the completed report to PDF only after all member placeholders and
truthful contribution values are resolved.
