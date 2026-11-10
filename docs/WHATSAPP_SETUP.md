# WhatsApp delivery — setup

Goal: after each scheduled run, the Team Uzair PDF goes out on WhatsApp from the company's
WhatsApp Business number to (a) chosen people and (b) one group.
Module: `mtd/whatsapp_send.py`. Settings: `config/whatsapp.json` (no secrets in the repo).

It uses the **official WhatsApp Cloud API** (Meta). Unofficial "WhatsApp Web" automation tools
break WhatsApp's terms and can get the business number banned, so they are not used.

## What WhatsApp allows (2026)
| | Individual numbers | Group |
|---|---|---|
| Possible via official API | Yes | Only for **Official Business Accounts** (green tick) |
| Which group | — | Only a group **created through the API**; people join via its invite link. An existing WhatsApp group cannot be posted to. |
| Size | — | Max **8 participants** |
| Number in WhatsApp Business app (coexistence) | Yes | **No**, groups need a Cloud-API-only number |
| Message | Approved **template** with the PDF attached (required for scheduled, business-initiated messages) | Same |
| Cost | Meta charges per delivered message (utility rate) | Charged **per participant** who receives it |

**If the group can't be used** (no green tick, more than 8 people, or the number stays in the
Business app), list the group members as individual recipients instead. Everyone still gets the
same PDF and message at 12:00, but one-to-one rather than in a shared group.

## Steps for you (one time)

1. **Meta Business account**: business.facebook.com. Complete **Business Verification**
   (company documents) under Security Centre. Templates and higher limits need it.
2. **Add WhatsApp to Meta**: developers.facebook.com → create an App (type *Business*)
   → add the **WhatsApp** product → WhatsApp Manager.
3. **Connect your number**:
   - to keep using the WhatsApp Business app on the same number, choose
     **"Connect a WhatsApp Business App number" (coexistence)** and scan the QR code from the app.
     This works for numbers; it does not allow the Groups API.
   - or register a number for the Cloud API only. This is needed for the Groups API; that number then stops working in the app.
4. **Copy two IDs** from WhatsApp Manager → API Setup: **Phone number ID** and **WhatsApp Business Account ID**.
5. **Create a permanent access token**: Business Settings → Users → **System users** → add (Admin)
   → assign the App and the WhatsApp account → *Generate token* with permissions
   `whatsapp_business_messaging` and `whatsapp_business_management`, expiry **Never**.
   **Do not paste the token in chat.** I will open a secure form for it (step 8).
6. **Create the message template** in WhatsApp Manager → Message templates:
   - Name `mtd_daily_report`, Category **Utility**, Language **English (en)**
   - Header: **Document**
   - Body (copy exactly):
     ```
     MTD revenue report {{1}} — {{2}}
     MTD revenue: {{3}} ({{4}})
     Achievement: {{5}} of pro-rated target
     Enrollments: {{6}}
     The full report is attached.
     ```
   - Sample values: `Nov 1-9, 2026` · `Team Uzair` · `Rs 23,07,426` · `-14.4% vs Oct 1-9` · `37%` · `49 (prev 71)`
   - Submit and wait for **Approved** (usually minutes to a day).
7. **Recipients**: send me the people's numbers with country code (e.g. 91…). Each person
   should have agreed to receive the report on WhatsApp. For the group, tell me whether your account has
   the green tick and who the (≤8) members are; otherwise I'll list them individually.
8. **Then tell me "WhatsApp is ready"**. I will:
   - ask you to approve opening the network to `graph.facebook.com` for this environment,
   - open a secure form where you paste the token (saved as an environment secret, never in the repo or chat),
   - fill `config/whatsapp.json`, send a **test to your own number**, and after you confirm,
     set `enabled: true` so every scheduled run sends automatically.

## Daily behaviour once enabled
After the PDF is built and pushed, the run calls
`python3 mtd/whatsapp_send.py --summary "reports/YYYY-MM/summary <Mon> 1-N.json"`:
it uploads the PDF once, sends the template to each enabled number/group and logs message ids
(names only, no numbers) in `reports/YYYY-MM/whatsapp_log.json`. Failures (for example an expired token or a
paused template) are reported in the brief, while email and chat delivery still go out.
Blocked runs (no sheet / sheet not updated) send nothing on WhatsApp.
