# Actual submission form — checked October 28, 2026

**Rechecked October 29, 2026:** authenticated Chrome again displayed all fields below,
including the required track/theme choices, public GitHub field, video-link field,
feedback fields and unchecked publication permission. Nothing was entered or submitted.
The official rules were read in the same session; age/majority, residence/sanctions,
employment exclusions, team size/authority and rights remain human attestations.
The official Meta event page still lists November 4 at 21:00 US Eastern, equivalent
to **November 5, 2026, 09:00 Bangkok**. No change to the documented deadline was found.

The authenticated form at [Submit Project](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit) was inspected in the existing Chrome session after authentication finished loading. No field was changed, no checkbox accepted, and nothing was submitted. Access to the form is verified; it does not independently establish every eligibility declaration.

| Visible field | Verified detail / prepared answer |
|---|---|
| Team Name | Text input. Entrant supplies the intended team name; “Reality Compiler” is suggested. |
| Team Members | Current account appears; Add Team Member control is available. Entrant confirms roster and authorization. |
| Which track are you submitting to? | Explicitly required: Indie Developer Track / Startups Track. Entrant chooses eligibility-appropriate track. |
| Which problem statement did you build towards? | Explicitly required: Build for Your World / Push the Frontier. Recommended: Push the Frontier. |
| Most Viral Track X post link | Optional competition wording. No post or viral claim prepared. |
| Project Description | Multiline input; copy in [submission-copy.md](submission-copy.md). |
| Public GitHub Repository | URL-like text input, GitHub URL placeholder. **Current repository is private.** |
| 3-Minute Demo Video | Text link input, YouTube URL placeholder. No direct file uploader was visible. |
| Describe your use of Meta products to build the submitted project | Multiline input; copy prepared. |
| Why are Meta's models important to your solution? | Multiline input; copy prepared. |
| Provide feedback from your experience using Meta products | Multiline input; factual technical feedback prepared. |
| Provide feedback from your experience using partner technologies. | Text input, Fireworks/Modal/Baseten placeholder. No use of these partners is claimed. |
| Publication/promotion permission | Unchecked consent checkbox granting Meta/Cerebral Valley use, publication, sharing and promotion. Human review/acceptance required. |
| Submit | Present; never clicked. |

No inspected input or textarea had an HTML `maxlength` limit (reported `-1`). This does **not** establish unlimited server-side limits. Only track/theme were explicitly marked required in the rendered text; no validation submission was attempted to discover hidden requirements. There was no separate project-title field in this form. No file-size, codec, hosting-provider restriction, or direct-upload limit was displayed. “3-Minute” is the actual label; whether it means exactly three minutes or a maximum is not explained. The prepared film is under three minutes.

The form does not ask for a deployed app URL. Neither inspected public rules nor this form establishes a deployment requirement. Private repository access and downloadable-bundle substitution are **not documented as accepted alternatives**. A local package is useful supplementary evidence, not proof that a private repository meets the Public GitHub Repository field.

## Rules and deadline

[Official Meta event page](https://dev.meta.ai/events/global-hackathon) and [Cerebral Valley official rules](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/waiver), rechecked October 28: deadline November 4, 2026, 21:00 US Eastern = **November 5, 2026, 09:00 Bangkok**. Organizer changes remain possible.

Project criteria: impact 30%, use of Meta AI tooling 25%, technical depth/execution 20%, demo 25%. These differ from the equally weighted application criteria. One project enters one track. Indie teams may have up to four members; teams appoint an authorized representative and identify all members. Startup representatives must be authorized active employees. Acceptance, age of majority/18+, residence and other listed restrictions remain entrant attestations. The user's prior acceptance is reported, not replaced by an automated eligibility decision.

The rules require appropriate rights and license compliance and grant organizers broad use of submitted materials. The form also asks for publication/promotion consent. Reading them did not accept them. The entrant must review these terms personally before submission.

## Safest practical delivery

Prepare a sanitized source archive and the generated-only film locally. After the entrant's review, the straightforward route matching the form is an approved public source repository plus an approved hosted demo link. **Do not change visibility or upload automatically.** A separate sanitized public submission repository would avoid publishing private history, but creating/publishing it also needs approval. If the entrant wants private delivery, obtain organizer confirmation of the alternative; no request was sent. Existing private PR links alone are insufficient for an unauthenticated judge.
