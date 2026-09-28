# MuseDouble prototype: integration handoff

> Historical prototype notes. The current PHP backend implements real accounts,
> administration, image/reference generation and private results. See README.md
> and BACKEND.md for the current installation and scope. Historical `dist/`
> paths below refer to files now located at the repository root.

The current site is a static prototype. Registration, identity review, contracts, model training, billing, generation, and support delivery are simulated. Uploaded files stay in browser memory and disappear on reload. Only language preference persists locally.

## Onboarding contract

- Require at least **50 distinct accepted personal photos**, JPEG/PNG/WebP, each no larger than 20 MiB. Stock samples do not count. More than 50 is allowed.
- The UI prevents selecting the same file metadata twice. The backend must revalidate type, size, count and duplicates based on actual file content; client metadata is not trustworthy.
- Collect scope explicitly: `covered` (default: do not recreate intimate areas), or `fuller` (optional body references, limited to individually authorized areas).
- Implement explicit boundary notes (up to 2,000 characters), persist scope and notes on the backend, and show them again for review. The current presentation does not implement that persisted record.
- Full-body reference photography does **not** require nudity. The creator may take every view clothed. Choosing fuller references does not authorize all kinds of output.
- Before training, the review team must resolve notes into explicit allowed/excluded areas and permitted content types, confirm those boundaries with the creator, and record affirmative consent with policy/contract versions and timestamps. A radio button or uploaded photo is not sufficient blanket authorization.
- Enforce those permissions in training, generation and agency access, not just the UI. Changes to consent need an explicit update/review flow and an effective timestamp.
- Complete adult identity verification and signing before payment is enabled. Implement authenticated private file storage and authorization checks before accepting real material. The anatomical guide images are static reference assets, not authenticated/private uploads.

## Existing demo flow

`draft → review → approved → training → ready`; requests for clearer photos return to `draft`. Production callbacks must replace the demo approval and model-ready buttons.

Activation is USD 250 including preparation, first month and 200 photos. The first monthly period begins when the model is ready. Renewal is USD 100/month for 200 photos; extra packs are USD 50 for 100 photos. Cancellation stops renewal while retaining paid-period access. Enforce balances and billing events server-side. Payment provider is not integrated.

## Frontend files

- `dist/app.js`: original shell and demo tools.
- `dist/membership.js`: demo account, review and membership state.
- `dist/i18n.js`, `dist/locales*.js`: six-language UI, English default.
- `dist/showcase.js`: public examples and image viewer.
- `dist/onboarding.js`: photo guide and 50-photo gate. Explicit scope/notes collection and persistence must be integrated.
- `dist/assets/onboarding/`: user-supplied illustrated guides. Embedded English labels remain unchanged; surrounding instructions are translated.

Do not treat demo flags, browser counters, WebMCP navigation or client-side gates as production authorization. Replace the in-memory state with authenticated APIs and retain all onboarding constraints above.

## September 19 access and copy update
- Root URL opens Home. Private studio routes redirect visitors to signup; Home, signup, login and support remain public.
- Email signup keeps the existing in-memory presentation flow. It does not create a server account. Login does not accept an arbitrary email as authentication. Google shows an unavailable message until configured; it never invents a Google identity.
- Replace registerMember/loginMember with verified email auth and restore member from a server session; support Google OAuth with state/PKCE and a verified callback. window.MUSEDOUBLE_AUTH.googleUrl is the optional server-owned OAuth start URL. Protect APIs and uploaded files server-side. Client routing is not authorization.
- Sign out clears in-memory account state and private file previews. Reload currently clears registration.
- Internal demo banners and review/training simulation controls are removed from presentation. Backend callbacks must drive approved/training/ready transitions. Notes about incomplete integrations belong here, not in marketing copy.
- Footer points to https://partners.musedouble.com. DNS/hosting for that domain are separate from this publication.
- First month begins when model is ready. Rollover of included photos and expiry of addon photos are UNDECIDED; do not invent a production policy. Existing cancellation copy preserves access until the paid period ends; backend must enforce that end date.
- dist/access.js adds routing, entry screens, translations and public copy cleanup. English plus Spanish, French, Russian, Portuguese and German remain available.
