# Chapter 5: System Implementation, Testing and Evaluation

## 5.1 Introduction

This chapter presents the implementation, testing, and evaluation of the MindBridge platform. It explains how the main parts of the system, including the WhatsApp onboarding and weekly check-in chat flows, the hybrid risk detection engine, the counsellor alert service, and the web-based counsellor and administrator portals, were built, connected, and tested to meet the project objectives.

The chapter starts with the implementation environment, covering the hardware specifications, software tools, external services, and local setup steps used to build and run the prototype. It then covers the preparation of the multilingual sentiment dataset, the fine-tuning of the DistilBERT model, the database tables, and the core application workflows. After that, it presents the testing strategy, the test cases and bug fixes, and the evaluation results of the DistilBERT model and hybrid detection engine across English, Kiswahili, Sheng, and code-switched messages. The final sections cover the Git version control evidence, a declaration on how AI tools were used during the project, and a discussion of the overall findings and limitations.

## 5.2 Implementation Environment

This section outlines the hardware, software, and service configurations used to build, train, and test the MindBridge prototype. Development and testing were carried out across two main environments: a local Windows laptop for backend coding, database management, and system testing, and a Kaggle cloud GPU session for fine-tuning and evaluating the DistilBERT sentiment model. Because mental health tools for minors involve strict ethical and privacy rules, the project was not deployed to a live server or tested on real patients. Instead, it was run and evaluated locally as a working prototype using synthetic participant profiles, and live WhatsApp chats connected through the Green API gateway.

### 5.2.1 Hardware Environment

On the user side, MindBridge was built around the everyday phone limits faced by young people in Kibera, Mathare, and Mukuru. Because all conversations take place inside WhatsApp and all risk checks run on the backend, a participant only needs an entry-level Android smartphone capable of running WhatsApp on a normal 3G or 4G mobile data bundle. Counsellors and system administrators access the web dashboard from a standard laptop or desktop computer using a web browser.

All coding, webhook testing, and local database work were done on a 64-bit Windows 11 laptop with an AMD Ryzen 5 5625U processor, 8 GB of RAM, and SSD storage. Running the trained DistilBERT model on the laptop's CPU was fast enough for scoring individual check-in messages during local testing, but fine-tuning the transformer model across the training dataset needed a dedicated graphics card. Model training and evaluation were therefore run on a Kaggle cloud session using an NVIDIA Tesla T4 GPU with 16 GB of video memory and 16 GB of system RAM. Table 5.1 summarises the hardware environment and minimum tested specifications across each part of the project.

**Table 5.1: Implementation environment and minimum requirements**

| Item or layer | Minimum tested specification or version | Purpose and justification | Evidence or source |
| :--- | :--- | :--- | :--- |
| **Client device for participant** | Android smartphone with Android 6.0+, 1 GB RAM, 100 MB free space, WhatsApp installed, 3G or 4G data | Allowed participants to complete onboarding, send 1 to 5 mood scores, write check-in notes in English, Kiswahili, or Sheng, and book sessions on WhatsApp. | Tested on live WhatsApp chats connected through the Green API gateway. |
| **Client device for counsellor and admin** | Dual-core laptop or desktop, 4 GB RAM, 1280x720 screen, modern web browser such as Chrome, Edge, or Firefox | Displayed the Counsellor Dashboard, four-week Chart.js mood trend graphs, flagged participant profiles, and Administrator Panel. | Verified across local desktop browser testing. |
| **Local development laptop** | AMD Ryzen 5 5625U 6-core processor at 2.30 GHz, 8 GB RAM, 50 GB free SSD space, Windows 11 64-bit | Ran the Django backend, local database, CPU-based DistilBERT sentiment checks, and automated test suite across all four sprints. | Local system profile and local development test measurements against the 3.0-second response time design target. |
| **Machine learning training runtime** | Kaggle cloud session with 1x NVIDIA Tesla T4 GPU with 16 GB VRAM, 4 vCPUs, 16 GB RAM | Used to fine-tune and evaluate the DistilBERT sentiment model across English, Kiswahili, Sheng, and code-switched messages. | Kaggle training log and saved model files in the sentiment model folder. |

As shown in Table 5.1, training the model on Kaggle's GPU while running the web app on a regular laptop CPU kept the prototype practical and lightweight. Once the DistilBERT model finished training on the Tesla T4 GPU and its weights were saved to disk, the Django backend could run live sentiment checks on the laptop CPU without needing expensive hardware.

### 5.2.2 Software, Services and Configuration

The software tools were chosen so that database storage, WhatsApp messaging, and natural language processing could all run together inside one Python project. The specific tools and versions used during implementation are listed below:

1. **Operating System and Python Environment**: Development and testing were done on Microsoft Windows 11 Home Single Language 64-bit using Python 3.13 inside a dedicated virtual environment so project packages stayed isolated from the rest of the computer.
2. **Backend Framework and Frontend Templates**: Django 5.2 served as the main web framework, handling webhook URLs, user login, role-based access control, database queries, and custom management commands (Django Software Foundation, 2025). The Counsellor Dashboard and Administrator Panel were built with server-rendered Django Templates using HTML5 and CSS, with Chart.js used on the participant profile page to draw the four-week mood line charts.
3. **Database Management**: The system was configured to support PostgreSQL 16 through the psycopg 3.2 adapter for relational storage alongside SQLite 3 for local development and automated test runs (PostgreSQL Global Development Group, 2025). The database stored participant profiles, counsellor accounts, mood ratings, weekly check-ins, session bookings, risk alerts, and the multilingual keyword library.
4. **Machine Learning and NLP Libraries**: The sentiment pipeline was built with Hugging Face Transformers 4.57.6 and PyTorch, using the CPU version on the local laptop and CUDA on Kaggle for GPU training (Paszke et al., 2019; Wolf et al., 2020). SafeTensors was used to store the trained model weights safely, while Scikit-learn, Pandas, and NumPy were used for text cleaning, splitting the dataset, calculating Cohen's kappa agreement between raters, and computing Precision, Recall, and F1-Score metrics (Cohen, 1960; Pedregosa et al., 2011).
5. **WhatsApp Gateway and Development Tools**: Two-way WhatsApp messaging was connected through the Green API WhatsApp gateway alongside webhook handlers for incoming messages (Green API, 2025). Visual Studio Code was used for writing and debugging code, Postman was used to send test JSON payloads to the webhook URLs, and Git and GitHub were used for version control and automated test runs.
6. **Environment Variables and Security Settings**: Sensitive settings such as the Django secret key, database credentials, and Green API instance tokens were kept in a local environment file that was ignored by Git. A clean example template file was committed to the repository to show which settings are needed to run the app. Session and CSRF cookies were set to HTTP-only access, clickjacking protection was turned on, and the project timezone was set to Nairobi time.

### 5.2.3 Local Setup and Reproducibility

To make the project easy to set up and test on another computer, all required Python packages were listed in three requirement files in the project root folder: one for the core Django web app, one for CPU-based DistilBERT sentiment inference, and one for the Kaggle model training tools.

Setting up and running the project locally followed a simple step-by-step sequence in the terminal: creating and activating the virtual environment, installing the requirement files with pip, running database migrations, and creating an administrator account. Running the custom `prepare_test_data` management command loaded the starter keyword library of 193 phrases from `care/keyword_library.py` across English, Kiswahili, and Sheng, which was then expanded by 4 additional Tier-1 crisis phrases added through the administrator keyword workspace to reach the final total of 197 active phrases in the local database. The command also created three sample counsellor accounts for Amina Otieno, Brian Mwangi, and Grace Wanjiru, created sample participant profiles across Kibera, Mathare, and Mukuru, and added open appointment slots for testing. Running `check_sentiment` verified that the local DistilBERT model loaded properly and that sentiment risk contribution was enabled, and running `check_system` checked migrations, counsellor availability, and active keywords before starting the local server with `runserver`. Running the `run_green_api_poller` command connected the local Django server directly to the linked Green API WhatsApp instance over HTTPS so live WhatsApp messages and replies could be tested end to end.

## 5.3 System and Model Implementation

This section explains how the system was built in practice. Implementation covered two main areas: first, preparing the multilingual youth sentiment dataset and fine-tuning the DistilBERT model; and second, building the database tables, the WhatsApp chat flows, the three-layer hybrid risk detection engine, and the counsellor and administrator web pages in Django.

### 5.3.1 Dataset Description, Preparation and Partitioning

To identify emotional distress among adolescent boys in Nairobi's informal settlements, the sentiment model needed training examples that looked like real messages sent by young people in Kibera, Mathare, Kawangware, Mukuru, and Korogocho. Standard sentiment datasets are almost entirely in formal English and fail when a participant mixes Kiswahili, Sheng slang, and English in the same sentence. Because collecting private WhatsApp chats from real minors was not ethically permitted, a dataset of 762 labelled check-in messages was put together using the project's dataset builder script and checked with the data audit script.

The dataset combined three internal sets of messages: the MindBridge gold-standard examples, the Kenyan conversational set, and adapted youth mental health expressions rewritten into everyday Nairobi phrasing. Every message was given one of three sentiment labels, either negative, neutral, or positive, and marked with one of four language styles: English, Kiswahili, Sheng, or code-switched. To make sure the labels were reliable before training the model, every message was independently labelled by two raters, and any differences were reviewed and agreed on. Across the training split, the two raters agreed on 94.23% of the messages, giving a Cohen's kappa score of 0.9134, which showed strong consistency across all four language styles (Cohen, 1960).

Before splitting the dataset for training and evaluation, the messages went through four preparation steps:

1. **Text Cleaning**: Messages were cleaned by standardising apostrophes and punctuation, fixing inconsistent spacing, and tidying up formatting so spelling differences would not confuse the model.
2. **Filtering Out Very Short Replies**: During live chat handling, replies with fewer than three words, such as single-digit mood scores or one-word greetings like *"Sasa"* or *"Poa"*, were skipped by the sentiment model because two words do not give enough context for sentiment classification. Those short replies were handled by the mood score and keyword rules instead.
3. **Token Length Verification**: Using the DistilBERT tokeniser with a maximum length of 512 tokens, the data audit confirmed that none of the 762 messages were cut short and almost every word was cleanly tokenised.
4. **Keeping Related Scenarios Together During Splitting**: Because several messages in the dataset were written as English, Kiswahili, and Sheng versions of the same situation, messages from the same scenario were linked under a shared group ID across 395 unique groups. When splitting the dataset into training, validation, and test sets, whole groups were kept together so the same underlying scenario would never appear in both the training set and the test set.

Table 5.2 shows how the 762 labelled messages were divided across the training, validation, and test sets by sentiment label and language category.

**Table 5.2: Multilingual sentiment dataset composition and group-stratified splits**

| Partition or Subset | Total Records | Unique Groups | Negative | Neutral | Positive | English | Kiswahili | Sheng | Code-Switched |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Training Split (68.2%)** | 520 | 276 | 172 | 176 | 172 | 155 | 132 | 109 | 124 |
| **Validation Split (17.5%)** | 133 | 59 | 49 | 44 | 40 | 32 | 39 | 31 | 31 |
| **Held-Out Test Split (14.3%)** | 109 | 60 | 31 | 36 | 42 | 35 | 29 | 20 | 25 |
| **Total Corpus (100.0%)** | **762** | **395** | **252** | **256** | **254** | **222** | **200** | **160** | **180** |

As shown in Table 5.2, the dataset was evenly balanced across the three sentiment classes with 252 negative, 256 neutral, and 254 positive messages, while giving strong representation to Kiswahili with 200 messages, code-switched text with 180 messages, and Sheng with 160 messages alongside 222 English messages.

### 5.3.2 DistilBERT Model Training and Selection

Once the dataset was ready, the sentiment model was fine-tuned on the Kaggle Tesla T4 GPU environment using the project's training notebook. The pre-trained `distilbert-base-uncased` model from Hugging Face was loaded with a three-class classification layer to predict negative, neutral, or positive sentiment (Sanh et al., 2019; Wolf et al., 2020).

DistilBERT was chosen over full BERT or larger multilingual models because it is about 40% smaller and much faster on a standard CPU, helping the Django application meet the three-second webhook response time design target. While the DistilBERT classifier itself assigns a negative, neutral, or positive label using standard three-class probability selection, the hybrid risk detection engine uses a separate 0.85 confidence threshold to decide whether a negative sentiment prediction is strong enough to count as a risk-evidence signal. In an initial 3-epoch test run, training loss only dropped to 0.8854 and predicted confidence scores on negative messages stayed too low to pass that 0.85 hybrid risk threshold. Training was therefore extended to 8 epochs at 17 optimisation steps per epoch, for a cumulative total of 136 training steps across all eight epochs on the Kaggle T4 GPU, using the AdamW optimiser and validation macro F1-score to select the best checkpoint. Across the 8 epochs, validation macro F1 climbed from 0.5209 at epoch 1 to 0.8103 at epoch 3 and peaked at 0.8443 at epoch 7, with final training loss dropping to 0.3125 across a total cumulative training runtime of 31.97 seconds for all eight epochs. Because `distilbert-base-uncased` was pre-trained primarily for English, fine-tuning on the 520-message training split could not be assumed to give equal accuracy across Kiswahili, Sheng, and code-switched messages, making separate evaluation across each language category essential. The trained model weights and tokeniser files were downloaded from Kaggle and placed inside the project's `models/sentiment` folder alongside the evaluation reports in `models/sentiment_reports` so the Django backend could run sentiment checks locally without needing an internet connection. Figure 5.1 shows the training and validation log output from the fine-tuning process.

> **[INSERT SCREENSHOT HERE — Figure 5.1]**
> - **What to capture**: Open a terminal in `C:\Users\jadaw\OneDrive\MINDBRIDGE\mindbridge`, run `.\.venv\Scripts\python.exe manage.py check_sentiment`, and capture a screenshot of the formatted DistilBERT Fine-Tuning & Validation Log Summary and Held-Out Test Set Evaluation output.
> - **Caption to place below the image**: `Figure 5.1: DistilBERT Fine-Tuning and Validation Log Output`

As shown in Figure 5.1, the training pipeline checked that no conversation groups overlapped between the training and test sets, confirmed that no messages were cut off at the 512-token limit, and recorded both the pre-trained baseline scores and the post-training scores across all four language styles.

### 5.3.3 Database and Data Implementation

The database entities and relationships were built using Django models in `care/models.py` and created through sixteen migration files. To protect participant privacy under the Kenya Data Protection Act (2019) while giving counsellors clear records to review, the database tables were organised into five main groups:

1. **Participant Profiles**: The `Participant` table stored participants under a chosen nickname and a generated participant code such as `MB-1001` instead of real names. It recorded their WhatsApp number, age between 13 and 24, settlement area across Kibera, Mathare, Kawangware, Mukuru, or Korogocho, preferred language, current step in the chat flow, consent and under-18 assent timestamps, assigned counsellor, and any account deletion request date.
2. **Mood Entries and Weekly Check-Ins**: The `MoodEntry` table saved each 1-to-5 mood rating, optional free-text note, DistilBERT sentiment label and confidence score, sentiment risk eligibility flag, and the date recorded. The `WeeklyCheckIn` table tracked weekly check-in cycles for each participant and used a uniqueness rule so the system would only send one scheduled prompt per participant per week and could easily count missed weeks.
3. **Keywords, Risk Evidence, and Risk Alerts**: The `Keyword` table was seeded with 193 starter phrases from `care/keyword_library.py` and expanded by 4 administrator-added Tier-1 terms to store a final total of 197 active English, Kiswahili, and Sheng phrases divided into 43 Tier-1 immediate crisis terms and 154 Tier-2 supporting distress terms across categories such as immediate safety, hopelessness, self-worth, isolation, bullying, home safety, sleep issues, school and fee pressure, substance use, and emotional loss. The `RiskEvidence` table recorded individual signals from the behavioural, keyword, and sentiment layers over a rolling seven-day window, with `SENTIMENT_ENABLED=1` and `SENTIMENT_RISK_ENABLED=1` enabled in the Django configuration so that eligible negative sentiment predictions meeting the 0.85 risk threshold contributed to risk decisions. The `RiskAlert` table stored the triggered alerts along with their priority, reason, trigger source, open or reviewed status, 24-hour escalation timestamp, and the counsellor's review notes.
4. **Counsellors and Session Bookings**: The `CounsellorProfile` and `AssignmentRotation` tables managed active counsellor accounts and kept track of whose turn it was to receive the next registered participant under round-robin assignment. The `AvailabilitySlot`, `SessionRequest`, and `Session` tables managed open 30-minute counsellor time slots, in-chat booking requests, and confirmed or cancelled counselling appointments.
5. **Message Logs and Background Jobs**: The `InboundMessage`, `OutboundMessage`, and `WorkerStatus` tables recorded incoming and outgoing WhatsApp messages with unique IDs so webhook retries would not create duplicate replies, and tracked when background tasks last ran.

Table 5.3 shows how each part of the system design maps to the actual files and database tables in the MindBridge project.

**Table 5.3: Mapping of system design components to implemented MindBridge modules**

| System Design Component | Implemented Module and Files | Main Functions and Database Tables | Purpose in the Prototype |
| :--- | :--- | :--- | :--- |
| **WhatsApp Webhook Gateway** | `care/views.py`, `care/services.py`, `config/urls.py` | `green_api_webhook`, `run_green_api_poller`, `send_green_api_message`, `InboundMessage`, `OutboundMessage` | Receives incoming WhatsApp messages, checks webhook signatures, and sends replies back through Green API. |
| **Onboarding, Minor Assent and Round-Robin Assignment** | `care/services.py`, `care/workflows.py` | `process_message`, `assign_counsellor`, `Participant`, `CounsellorProfile`, `AssignmentRotation` | Guides new participants through consent, nickname, age, and under-18 assent, then assigns an active counsellor in turn. |
| **Hybrid At-Risk Detection Engine** | `care/risk.py`, `care/keywords.py`, `care/keyword_library.py`, `care/model_ports.py` | `assess`, `missed_checkin_signal`, `matches_keyword`, `classify_note`, `Keyword`, `RiskEvidence` | Runs the weekly mood rules, scans messages against the 197 multilingual keywords with negation checks, and runs DistilBERT sentiment classification. |
| **Alert Dispatch, 24h Escalation and Session Booking** | `care/workflows.py`, `care/services.py` | `create_alert`, `run_escalations`, `slot_prompt`, `book_appointment`, `RiskAlert`, `Session`, `AvailabilitySlot` | Sends emergency safety contacts on high-risk alerts, lets participants book open counsellor slots on WhatsApp, and escalates alerts unreviewed after 24 hours. |
| **Counsellor Dashboard and Participant Profiles** | `care/views.py`, `templates/care/dashboard.html`, `participant_detail.html`, `alerts.html`, `sessions.html` | `dashboard`, `alerts`, `participant_detail`, `review_alert`, `sessions`, `availability` | Gives counsellors a web portal to view flagged participants, inspect four-week Chart.js mood charts, review alerts, and manage sessions. |
| **Administrator Workspace and Data Retention** | `care/views.py`, `care/admin.py`, `templates/care/admin_dashboard.html` | `admin_dashboard`, `KeywordAdmin`, `ParticipantAdmin`, `enforce_retention` | Lets admins monitor counsellor caseloads, view overdue alerts, update keywords, purge mood and message records older than 12 months, and delete profiles within 30 days of a deletion request. |

### 5.3.4 Implemented Application Modules and Business Rules

As shown in Table 5.3, the backend code was split across four focused files inside the `care` app so that chat handling, risk checks, keyword matching, and dashboard views stayed easy to maintain:

1. **WhatsApp Onboarding and Chat Flow**: When a message arrived at the Green API webhook endpoint, the message handler guided new participants step by step through consent, choosing a nickname, entering their age, and completing under-18 assent before marking their profile active. Before any mood scores were saved, the participant had to reply `"I agree"`. If the participant entered an age between 13 and 17, the bot paused and asked them to reply `"I understand"` to a simple safeguarding message before assigning them to a counsellor. Active participants could also send plain commands at any time such as `"Pause"`, `"Check in"`, `"Privacy"`, `"Counsellor"`, or `"Delete my data"`.
2. **Negation-Aware Keyword Matching**: The keyword library was seeded with 193 starter phrases from `care/keyword_library.py` and expanded through the admin workspace to 197 active terms in the local database across English, Kiswahili, and Sheng. Because a simple word search would raise false alarms when a participant said they were safe, the keyword matcher in `care/keywords.py` checked up to four words before any matched phrase for negation words in English, Kiswahili, and Sheng such as `"don't"`, `"not"`, `"never"`, `"si"`, `"sitaki"`, `"hapana"`, and `"hakuna"`. If a participant wrote *"I don't want to die"*, the negation check blocked a false keyword alert. However, if the message had a contrast word like `"but"` or `"lakini"`, such as *"I don't want to die, but sometimes I want to die"*, the matcher checked the second part of the sentence on its own and still raised a crisis alert.
3. **Three-Layer Hybrid Risk Assessment**: Whenever an active participant sent a mood rating or a free-text note, the risk module checked three layers over a rolling seven-day window. First, if the message contained a Tier-1 crisis phrase such as `"want to kill myself"`, `"nataka kujiua"`, `"nitajinyonga"`, or `"nataka kujimaliza"`, the engine immediately raised a high-priority alert and replied with an urgent safety message instructing the participant to call Kenya emergency services on `999` or `112`, go to the nearest emergency department, or contact a trusted adult right away, without waiting for a second signal. Second, the behavioural layer checked whether the participant had recorded a mood score of 2 or below across three separate calendar weeks, had a sudden mood drop of 3 or more points between check-ins, or had missed two weekly check-ins in a row. Third, with `SENTIMENT_ENABLED=1` and `SENTIMENT_RISK_ENABLED=1` enabled in the Django configuration, Tier-2 distress keywords and eligible negative DistilBERT predictions whose confidence met or exceeded the hybrid risk engine's 0.85 threshold (`RISK_NEGATIVE_THRESHOLD`) were logged as supporting evidence; because `distilbert-base-uncased` was pre-trained as an English encoder, `care/model_ports.py` marks a sentiment prediction eligible for risk decisions only on English messages of three or more words, while recording the predicted label and confidence on Kiswahili and Sheng messages for counsellor visibility and relying on the multilingual keyword and behavioural mood layers for Kiswahili and Sheng risk evidence. Whenever two different layers logged evidence within seven days, a combined alert was created for the assigned counsellor.
4. **Counsellor Assignment, Session Booking, and Scheduled Tasks**: When a participant texted `"Counsellor"` or asked to speak with someone, the workflow module looked up open appointment slots for their assigned counsellor and sent them back as a numbered list on WhatsApp. Replying with a slot number booked the session, locked the time slot so another participant could not double-book it, and queued confirmation messages. Background commands handled weekly check-in prompts, 24-hour and 2-hour session reminders, escalating alerts left unreviewed for over 24 hours to the administrator dashboard, purging mood entries, messages, and risk records older than 12 calendar months, and permanently deleting participant profiles within 30 days of a `"Delete my data"` request.

### 5.3.5 End-to-End Integration and User Workflows

To verify that all parts of the platform worked together smoothly, complete participant journeys were run on live WhatsApp through the Green API webhook handler and poller service. Figure 5.2 shows the WhatsApp onboarding, under-18 assent step, and weekly mood check-in flow.

> **[INSERT SCREENSHOT HERE — Figure 5.2]**
> - **What to capture**: With `python manage.py runserver` and `python manage.py run_green_api_poller` running, open your live WhatsApp chat (on WhatsApp Web/Desktop or your phone) with the MindBridge WhatsApp number. Capture a screenshot showing the live WhatsApp onboarding flow (`"I agree"` -> nickname -> age `16` -> `"I understand"` -> area `"Kibera"`) followed by a mood score of `2` and a code-switched check-in note.
> - **Caption to place below the image**: `Figure 5.2: WhatsApp Onboarding, Minor Assent, and Weekly Mood Check-In Workflow`

As shown in Figure 5.2, the bot walks the participant through consent and nickname registration in friendly everyday language, asks for explicit assent when an age under 18 is entered, and saves both the numeric mood score and the follow-up text note in the same chat thread.

When a participant sends a message with a self-harm phrase or asks to talk to a counsellor, the chat flow immediately switches to crisis support and appointment booking. Figure 5.3 shows the Tier-1 crisis response and in-chat session booking workflow.

> **[INSERT SCREENSHOT HERE — Figure 5.3]**
> - **What to capture**: In your live WhatsApp chat with the MindBridge number, send a Tier-1 crisis test phrase such as *"Nimechoka kuishi, nataka kujiua"* followed by `"Counsellor"` and `"1"` to pick the first available time slot. Take a screenshot of the live WhatsApp conversation showing the urgent safety reply with Kenya emergency services (`999` or `112`), nearest emergency department and trusted adult guidance, the numbered appointment slots, and the booking confirmation.
> - **Caption to place below the image**: `Figure 5.3: Tier-1 Crisis Override, Helpline Dispatch, and In-Chat Session Booking`

In Figure 5.3, as soon as the Tier-1 phrase is detected, the bot replies with urgent safety guidance and Kenya emergency numbers `999` and `112` alongside numbered time slots from the assigned counsellor's schedule so the participant can confirm an appointment by replying with a single number.

On the web portal side, counsellors log in to check on their assigned participants and review open risk alerts. Figure 5.4 presents the Counsellor Dashboard interface.

> **[INSERT SCREENSHOT HERE — Figure 5.4]**
> - **What to capture**: Log into `http://127.0.0.1:8000/` as counsellor `amina.otieno` and capture a screenshot of the Counsellor Dashboard showing the summary cards, the open risk alerts for assigned participants such as Kelvin Otieno (`MB-1001`) and Klein (`MB-474866EDB894`), and the participant list.
> - **Caption to place below the image**: `Figure 5.4: Implemented Counsellor Dashboard and Flagged Participant Queue`

As shown in Figure 5.4, the dashboard places unreviewed high-risk and medium-risk alerts right at the top of the page after login, displaying each participant's nickname, settlement area, latest mood score, and the detection source that triggered the alert.

Clicking on a flagged participant opens their detailed profile page so the counsellor can see their full check-in history before reaching out. Figure 5.5 shows the Flagged Participant Profile view.

> **[INSERT SCREENSHOT HERE — Figure 5.5]**
> - **What to capture**: From the Counsellor Dashboard, click on Kelvin Otieno (`MB-1001`, `/participants/8/`) or Klein (`MB-474866EDB894`, `/participants/41/`). Take a screenshot showing the four-week Chart.js mood trend graph, the check-in message log with DistilBERT sentiment labels, and the alert review form.
> - **Caption to place below the image**: `Figure 5.5: Flagged Participant Profile View with Four-Week Chart.js Mood Trend and Risk Evidence`

In Figure 5.5, the counsellor can see both the four-week mood line graph and the exact messages, matched keywords, and sentiment predictions that raised the alert before recording a review outcome such as confirmed risk, false positive, session booked, or follow-up needed.

System-wide monitoring, counsellor caseloads, and updates to the multilingual keyword library are managed through the Administrator Workspace and Django Admin pages, as shown in Figure 5.6.

> **[INSERT SCREENSHOT HERE — Figure 5.6]**
> - **What to capture**: Log in with your admin account `jadaw` and open `http://127.0.0.1:8000/workspace-admin/`. Take a screenshot showing the 5 registered participants, open alerts, the 3 counsellors (Amina Otieno, Brian Mwangi, Grace Wanjiru), and the active 197-phrase keyword library status.
> - **Caption to place below the image**: `Figure 5.6: Implemented Administrator Workspace and Multilingual Keyword Library`

As shown in Figure 5.6, the administrator dashboard gives a clear view of all registered participants and their assigned counsellors, highlights any alerts left unreviewed for more than 24 hours, shows the status of the 197 active Tier-1 and Tier-2 keywords, and links directly to the keyword editor so new Sheng or Kiswahili terms can be added at any time.

---

## 5.4 System Testing and Evaluation

To make sure the MindBridge prototype worked as intended and met its requirements, the system was tested using automated software tests alongside an evaluation of the fine-tuned DistilBERT model across English, Kiswahili, Sheng, and code-switched test messages.

### 5.4.1 Test Strategy and Acceptance Criteria

Testing was carried out across four levels:

1. **Unit Testing**: Focused tests checked individual functions in isolation, including text cleaning, the four-word negation check in the keyword matcher, contrasting clauses after words like `"but"` or `"lakini"`, grouping low mood ratings by calendar week, sudden mood drops of 3 or more points, and skipping sentiment checks on very short replies under three words.
2. **Integration Testing**: Integration tests checked how different parts of the backend worked together, including receiving Green API webhook payloads, saving records to the database, assigning counsellors in round-robin order, combining risk signals across layers, and queueing outbound messages without sending duplicates.
3. **System and Workflow Testing**: End-to-end tests walked through complete participant journeys from initial WhatsApp consent and under-18 assent through logging moods, triggering crisis alerts, booking a counselling slot, reviewing alerts on the counsellor dashboard, escalating overdue alerts after 24 hours, and purging old records and deleting profiles under the data retention rules.
4. **Access Control and Usability Testing**: Security checks confirmed that unauthenticated visitors were redirected to the login page, counsellors could only view participants assigned to their own caseload, and administrators could monitor system performance without changing clinical alert reviews.

A feature was accepted as passing only when all automated tests ran without errors, invalid inputs such as out-of-range ages or mood scores were rejected cleanly, local webhook processing stayed within the 3.0-second response time design target, and Tier-1 crisis phrases triggered an immediate high-risk alert every time.

### 5.4.2 Functional, Boundary and Negative Test Cases, Defects and Retesting

A total of 139 automated tests were written and run in the `care` application test suite using the single test command `python manage.py test care`, with all 139 tests passing. Figure 5.7 shows the terminal output from running the system checks and the `care` automated test suite.

> **[INSERT SCREENSHOT HERE — Figure 5.7]**
> - **What to capture**: Open a terminal in `C:\Users\jadaw\OneDrive\MINDBRIDGE\mindbridge` and run `.\.venv\Scripts\python.exe manage.py check_system` and `.\.venv\Scripts\python.exe manage.py test care`. Capture a screenshot showing the passing checks (`Sentiment risk mode: enabled for explicit evaluation`) and the exact command output `Ran 139 tests ... OK`.
> - **Caption to place below the image**: `Figure 5.7: Automated Django Test Suite and System Readiness Verification Output`

As shown in Figure 5.7, the system check verified database migrations, active counsellor rotation, the active keyword library, and the enabled sentiment risk configuration, and all 139 automated test cases in the `care` test suite passed. Table 5.4 summarises 15 key functional, boundary, and negative test cases from the `care` suite.

**Table 5.4: End-to-end functional, boundary, and negative test cases and results**

| Test ID | Requirement | Test Level and Type | Scenario and Test Input | Expected Result | Actual Result Observed | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-01** | `FR-01`, `NFR-05` | System positive and boundary | New participant aged 16 sends `"Hello"`, `"I agree"`, `"Jayden_K"`, and `"16"`, then tries to log mood `"2"` before sending `"I understand"`. | Account stays incomplete and blocks mood logging until under-18 assent `"I understand"` is received. | Mood `"2"` was blocked before assent; once `"I understand"` was sent, onboarding completed and mood `"3"` was saved. | **PASS** |
| **TC-02** | `FR-01` | Unit negative boundary | Participant in onboarding enters invalid ages `"12"` and `"25"` outside the 13 to 24 target range. | Bot rejects both numbers, leaves age empty, and asks for a valid age between 13 and 24. | Neither `12` nor `25` was saved, and the participant stayed on the age step until a valid age was entered. | **PASS** |
| **TC-03** | `FR-02` | Integration positive | Two active counsellors `c1` and `c2` are available; three participants `A`, `B`, and `C` onboard; `c2` is then marked inactive before `D` joins. | `A` goes to `c1`, `B` to `c2`, `C` to `c1`, and `D` goes to `c1` after `c2` is deactivated. | Assignments matched the round-robin order and skipped the inactive counsellor cleanly. | **PASS** |
| **TC-04** | `FR-03`, `FR-05` | Integration positive | Run the weekly check-in job twice for a participant who missed two previous weekly check-ins. | Queues only one check-in prompt for the current week and raises one missed check-in alert. | Created one outbound prompt and one `"Two missed weekly check-ins"` alert with no duplicates. | **PASS** |
| **TC-05** | `FR-04`, `FR-05` | Unit boundary | Participant submits low mood scores `2`, `2`, `2` on the same day versus across three separate calendar weeks. | Same-day low scores do not trigger the three-week rule; three separate low weeks trigger an alert. | Same-day entries were grouped into one week, while three separate low weeks raised `"Consecutive low weekly moods"`. | **PASS** |
| **TC-06** | `FR-06`, `FR-09` | System positive crisis override | Active participant sends Tier-1 phrase `"I intend to take my own life today"` or Sheng `"nimechoka kuishi"`. | Immediate high-priority alert without waiting for a second layer, and reply includes Kenya emergency numbers `999` or `112` and urgent safety guidance. | High-priority alert was created right away and emergency numbers `999` and `112` plus booking slots were returned in chat. | **PASS** |
| **TC-07** | `FR-06` | Unit negative negation check | Participant sends negated phrase `"I don't want to die"` versus mixed sentence `"I don't want to die, but sometimes I want to die"`. | Negated sentence does not raise a false keyword alarm; mixed sentence with `"but"` still raises a Tier-1 alert. | `"I don't want to die"` was ignored by the keyword negation check, while the mixed sentence raised a high-risk alert. | **PASS** |
| **TC-08** | `FR-07`, `FR-08` | Integration positive | With `SENTIMENT_RISK_ENABLED=1` enabled, participant sends English Tier-2 note `"I feel hopeless about finishing school"` with an eligible negative DistilBERT score of 0.91 above the 0.85 risk threshold. | Both keyword and sentiment layers log evidence in `RiskEvidence` and raise a combined alert marked `"keyword, sentiment"`. | Combined medium-priority alert was created with `"keyword, sentiment"` as the trigger source and saved on the mood entry. | **PASS** |
| **TC-09** | `FR-07` | Unit boundary short text and language | Participant sends a two-word note `"Not good"` or a non-English note after submitting a mood score. | Sentiment module marks the note ineligible for standalone sentiment risk so short or non-English replies rely on the mood and keyword layers. | Notes under three words and non-English notes were marked `risk_eligible=False` and handled by the mood and keyword layers. | **PASS** |
| **TC-10** | `FR-10` | Integration negative double booking | Two participants assigned to the same counsellor view slot `1`; the first participant books `"1"`, and then the second participant replies `"1"`. | First participant books the slot; second participant is told the slot is taken and `"1"` is not saved as a mood score. | Only one session was created, the second participant received an unavailable notice, and no false mood score was logged. | **PASS** |
| **TC-11** | `FR-11`, `NFR-02`, `NFR-07` | System negative access control | Counsellor `c2` tries to open a participant profile and review an alert assigned to Counsellor `c1`; Admin tries to review a clinical alert. | Counsellor `c2` receives `HTTP 404`; Admin receives `HTTP 403` on clinical alert review while keeping access to the admin dashboard. | Cross-counsellor access was blocked with `404` and admin clinical review was blocked with `403`. | **PASS** |
| **TC-12** | `FR-09`, `FR-12` | Integration positive 24h escalation | An open alert stays unreviewed for 25 hours and the escalation job runs twice. | First run marks the alert escalated and displays it on the admin dashboard; second run does not duplicate it. | Alert was escalated once on the first run and appeared under overdue alerts on the admin dashboard. | **PASS** |
| **TC-13** | `FR-13`, `NFR-03` | Integration positive data retention | In `test_retention_and_deletion_request`, a 400-day-old mood entry and a current mood entry are created; the participant then texts `"Delete my data"` and 30 days pass before `enforce_retention` runs again. | First `enforce_retention` run purges the 400-day mood entry while keeping the current entry; `"Delete my data"` revokes consent immediately, and the second run permanently deletes the participant profile after 30 days. | The 400-day mood entry was purged while the current entry remained, consent was revoked immediately, and the participant profile was deleted after the 30-day window. | **PASS** |
| **TC-14** | `NFR-04`, `NFR-06` | Integration negative gateway fault | Unsigned request sent to webhook, malformed JSON payload sent, and network offline error simulated during outbound delivery. | Unsigned webhook returns `HTTP 403`, bad JSON is safely ignored, and failed delivery retries and succeeds when back online. | Unsigned request was rejected, malformed JSON did not crash the server, and queued message was marked `sent` on retry. | **PASS** |
| **TC-15** | `NFR-01`, `NFR-05` | System performance and usability (local environment) | Process 20 check-in webhook messages and load the Counsellor Dashboard, Participant Profile, and Admin Dashboard views in the local development environment. | Local webhook responses finish within the 3.0-second design target and web dashboard views render under 2.0 seconds with `HTTP 200`. | In the local development environment on the laptop CPU, webhook processing took 0.18 to 0.64 seconds and web pages rendered in under 0.25 seconds. | **PASS** |

During development and sprint testing, several bugs were found, fixed, and retested. Table 5.5 summarises the main bugs discovered during testing and how they were resolved.

**Table 5.5: Defects identified during testing, corrective fixes, and retesting outcomes**

| Defect ID | Module Affected | Description of Defect Observed | Cause of the Bug | How It Was Fixed | Retesting Outcome |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DEF-01** | Keyword matcher in `care/keywords.py` | Safe sentences like *"I don't want to die"* or *"Sitaki kujiua"* were falsely raising Tier-1 suicide alerts. | The first version of the keyword scanner only checked if the words appeared in the sentence without checking for negation words before them. | Added a four-word negation check before matched phrases for English, Kiswahili, and Sheng negations, while still catching sentences with `"but"` or `"lakini"`. | Retested with negated and mixed sentences in `TC-07`; false keyword alarms dropped to zero while mixed crisis sentences still raised alerts (**PASS**). |
| **DEF-02** | Mood rules in `care/risk.py` | Sending three low mood scores of 2 or below on the same day falsely triggered the consecutive weekly low mood alert. | The rule originally checked the last three mood entries in the database without checking whether they were from different weeks. | Updated the rule to group mood scores by calendar week before checking for three consecutive low weeks. | Retested in `TC-05`; multiple low scores on the same day no longer triggered a false three-week alert (**PASS**). |
| **DEF-03** | Availability view in `care/views.py` | When a counsellor deleted an unbooked time slot and tried to add the same time again, the database threw a duplicate error. | Removing an unbooked slot only marked it inactive instead of deleting the row, which clashed with the unique time rule for that counsellor. | Updated slot removal so unbooked slots are deleted cleanly while slots with a booked session are kept. | Retested by deleting and re-adding the same slot time; the slot was re-created without errors (**PASS**). |
| **DEF-04** | Message handler in `care/services.py` | When a participant replied `"1"` to pick an appointment slot, the bot sometimes saved `"1"` as a low mood score of 1. | Both appointment slot choices and 1-to-5 mood ratings used single numbers in the chat. | Separated slot booking replies from mood score logging when a participant has an open session booking request. | Retested in `TC-10`; picking slot `"1"` booked the session without logging a mood score (**PASS**). |
| **DEF-05** | Admin dashboard template in `templates/care/admin_dashboard.html` | Opening the Administrator Dashboard when a registered participant had no eligible counsellor assigned threw a `VariableDoesNotExist` template error. | Chaining `default` filters onto `p.counsellor.username` caused Django's template engine to look up `username` on `None` when `p.counsellor` was empty. | Replaced the chained filter with an explicit `{% if p.counsellor %}` conditional check before rendering the counsellor's name or `"Unassigned"`. | Retested with `test_no_auto_assignment_when_no_eligible_counsellor` and the full 139-test `care` suite; the Admin Dashboard rendered `HTTP 200` cleanly (**PASS**). |

### 5.4.3 DistilBERT Sentiment and Hybrid Risk Detection Evaluation

To evaluate the sentiment model quantitatively, the final 8-epoch fine-tuned DistilBERT checkpoint in `models/sentiment` was compared against the original pre-trained `distilbert-base-uncased` baseline on the held-out test set of 109 messages, which contained 31 negative, 36 neutral, and 42 positive messages across 60 conversation groups. All metrics were computed with Scikit-learn and saved in `models/sentiment_reports/baseline_test_metrics.json` and `models/sentiment_reports/test_metrics.json` (Pedregosa et al., 2011). Table 5.6 compares the overall three-class sentiment performance and the negative-class screening performance at the 0.85 hybrid risk threshold between the pre-trained baseline model and the fine-tuned MindBridge DistilBERT model on the 109 held-out test messages.

**Table 5.6: Pre-trained baseline vs. fine-tuned DistilBERT performance on held-out test set (N = 109)**

| Evaluation Metric | Pre-Trained Baseline (`distilbert-base-uncased`) | Fine-Tuned MindBridge DistilBERT (`models/sentiment`) | Improvement |
| :--- | :---: | :---: | :---: |
| **Overall Accuracy (%)** | 44.95% | **88.07%** | **+43.12%** |
| **Macro Precision (%)** | 36.41% | **89.69%** | **+53.28%** |
| **Macro Recall (%)** | 47.34% | **89.15%** | **+41.81%** |
| **Macro F1-Score (%)** | 36.17% | **88.18%** | **+52.01%** |
| **Weighted F1-Score (%)** | 36.50% | **88.37%** | **+51.87%** |
| **Negative Recall at 0.85 Risk Threshold (%)** | 87.10% (with 48 false alarms) | **100.00%** (31/31 on test set, 7 false alarms) | **+12.90% (41 Fewer False Alarms)** |
| **Negative F1-Score at 0.85 Risk Threshold (%)** | 50.94% | **89.86%** | **+38.92%** |

As shown in Table 5.6, fine-tuning DistilBERT for 8 epochs on the Kenyan youth dataset produced a major improvement across every metric on the held-out test set. Before fine-tuning, the pre-trained baseline only got 44.95% of the messages right and had a macro F1-score of 36.17%. It failed to predict a single neutral message and treated unfamiliar Kiswahili and Sheng words as negative, causing 48 false alarms out of 78 non-negative messages. After fine-tuning, overall three-class accuracy jumped by 43.12 percentage points to 88.07% and macro F1 rose by 52.01 percentage points to 88.18%. When evaluated at the 0.85 negative confidence threshold used by the hybrid risk engine, the fine-tuned model achieved 100.00% recall on the 31 negative messages in the 109-message test set, catching all 31 negative test messages and cutting false alarms down from 48 to 7, which raised thresholded negative F1 from 50.94% to 89.86% on that test split.

To see how the fine-tuned model performed across each sentiment class and across the four languages used by participants in the settlements, Table 5.7 breaks down the held-out test results by class and language category.

**Table 5.7: Fine-tuned DistilBERT class-wise and language-subset performance on held-out test set**

| Evaluation Breakdown | Sample Size | Accuracy (%) | Precision (%) | Recall (%) | F1-Score (%) | Baseline F1 (%) for Comparison |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **By Sentiment Class (109 Total Messages)** | | | | | | |
| Negative (Distress or Low Mood) | 31 | - | 72.09% | 100.00% | **83.78%** | 52.63% |
| Neutral (Everyday Check-in) | 36 | - | 96.97% | 88.89% | **92.75%** | 0.00% |
| Positive (Coping or Good Mood) | 42 | - | 100.00% | 78.57% | **88.00%** | 55.88% |
| **By Language Category (Macro Averages)** | | | | | | |
| **English** | 35 | **97.14%** | 96.67% | 97.92% | **97.17%** | 54.48% |
| **Kiswahili** | 29 | **89.66%** | 93.33% | 91.67% | **91.53%** | 18.33% |
| **Code-Switched (English, Kiswahili, Sheng)** | 25 | **88.00%** | 90.30% | 85.86% | **86.60%** | 25.19% |
| **Sheng** | 20 | **70.00%** | 75.00% | 86.67% | **71.67%** | 14.42% |

As shown in Table 5.7, the model improved across all four language groups on the test split, while also reflecting the fact that `distilbert-base-uncased` was originally pre-trained for English. On English check-ins, accuracy reached 97.14% with a macro F1 of 97.17%. On Kiswahili messages, macro F1 jumped from 18.33% on the baseline to 91.53% with 89.66% accuracy, catching all 12 Kiswahili negative test messages. On code-switched messages, accuracy rose from 36.00% to 88.00% and macro F1 increased from 25.19% to 86.60%, catching all 8 code-switched negative test messages with zero false alarms at the 0.85 risk threshold. On pure Sheng messages, accuracy rose from 20.00% to 70.00% and macro F1 increased from 14.42% to 71.67%. While the model caught both negative Sheng test messages, it also misclassified 6 positive Sheng slang messages as negative, giving a 25.00% negative precision on Sheng alone. Table 5.8 presents the confusion matrix for the fine-tuned DistilBERT model across all 109 test messages.

**Table 5.8: Confusion matrix for fine-tuned DistilBERT sentiment classifier on the held-out test set**

| Actual Sentiment Class ↓ \ Predicted Class → | Predicted: Negative | Predicted: Neutral | Predicted: Positive | Total Actual | Class Recall (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Actual: Negative** | **31** | 0 | 0 | 31 | **100.00%** |
| **Actual: Neutral** | 4 | **32** | 0 | 36 | **88.89%** |
| **Actual: Positive** | 8 | 1 | **33** | 42 | **78.57%** |
| **Total Predicted** | 43 | 33 | 33 | **109** | **Overall Acc: 88.07%** |

As shown in Table 5.8, 96 out of the 109 test messages were placed into their exact true sentiment class, and all 31 actual negative distress messages in the test set were classified as negative, giving 100.00% negative recall on the 109-message test set. At the same time, 8 positive messages and 4 neutral messages, mostly written in heavy Sheng slang, were predicted as negative by DistilBERT on its own. In the MindBridge hybrid risk engine, those false alarms were prevented from triggering unnecessary counsellor alerts because a sentiment flag does not raise an alert by itself unless it is eligible and backed up by a second layer, namely a matched keyword from the 197-phrase library or a low weekly mood pattern. This confirmed that combining rule-based mood checks and local keywords with DistilBERT gives both strong sensitivity to distress and protection against false alarms on Sheng slang.

---

## 5.5 Version Control and Implementation Evidence

This section presents the Git version control setup, task tracking board, branching workflow, commit history, automated GitHub Actions test runs, and project organisation used while building MindBridge.

### 5.5.1 Repository Setup and Access

All project code, database migrations, dataset scripts, and automated tests were managed with Git and hosted on GitHub at `https://github.com/JaydaWalubiri/mindbridge`. Setting up the GitHub repository early in the project kept the codebase backed up in one central place and allowed the supervisor to review progress directly. Figure 5.8 shows the MindBridge GitHub repository overview and root folder layout.

> **[INSERT SCREENSHOT HERE — Figure 5.8]**
> - **What to capture**: Open `https://github.com/JaydaWalubiri/mindbridge` in your browser and capture a screenshot showing the repository header (`JaydaWalubiri / mindbridge`), branch indicator, root folders (`care`, `config`, `models`, `tools`, `templates`), and the top of the `README.md` file.
> - **Caption to place below the image**: `Figure 5.8: MindBridge GitHub Repository Overview and Root Directory Structure`

As shown in Figure 5.8, the repository separates the Django app inside `care`, project configuration inside `config`, dataset and training tools inside `tools` and `notebooks`, and the saved DistilBERT model and evaluation reports inside `models/sentiment` and `models/sentiment_reports`, along with a clear `README.md` setup guide.

### 5.5.2 Task Planning and Tracking

To keep development organised across the four Agile Scrum sprints, the system requirements were broken down into thirteen user stories from `US1` to `US13` and tracked using GitHub Issues and a GitHub Project board. Each issue card listed the user story description, acceptance criteria, sprint milestone, and topic labels for WhatsApp flows, risk detection, dashboard views, and privacy rules. Figure 5.9 shows the GitHub Project tracker and user story issues used to manage the sprints.

> **[INSERT SCREENSHOT HERE — Figure 5.9]**
> - **What to capture**: Open the **Issues** or **Projects** tab on `https://github.com/JaydaWalubiri/mindbridge` showing the user stories (`US1: WhatsApp Consent & Pseudonymous Onboarding` through `US13: Data Retention, Anonymisation & Deletion`) with their labels and completed statuses.
> - **Caption to place below the image**: `Figure 5.9: GitHub Project Tracker Board and User Story Issues`

Tracking each feature as a GitHub issue in Figure 5.9 made it easy to follow progress across sprints and ensured that none of the thirteen functional requirements were left out during coding.

### 5.5.3 Branching Strategy

Development followed a feature-branch workflow using the `main` branch and a dedicated feature branch named `feat/full-stack-care-workspace`. Rather than pushing unfinished changes straight to `main`, new features such as the hybrid risk engine, the Kaggle DistilBERT training scripts, the Counsellor Dashboard pages, and the Green API webhook handler were built and tested on the feature branch first before being merged into `main`. Figure 5.10 shows the branch structure of the repository.

> **[INSERT SCREENSHOT HERE — Figure 5.10]**
> - **What to capture**: Open `https://github.com/JaydaWalubiri/mindbridge/branches` in your browser (or run `git branch -a` in your terminal) and capture a screenshot showing the `main` branch and the `feat/full-stack-care-workspace` branch.
> - **Caption to place below the image**: `Figure 5.10: Repository Branch Structure and Feature Branch Workflow`

As shown in Figure 5.10, working on `feat/full-stack-care-workspace` kept the `main` branch stable while allowing regular testing and refinement of the NLP and WhatsApp components.

### 5.5.4 Commits and Development History

Progress across the project was recorded through regular, descriptive Git commits. Early commits created the Django project and database models for participants, mood entries, sessions, and risk alerts, followed by commits adding the WhatsApp onboarding flow, hybrid risk rules, counsellor round-robin assignment, and dashboard views, expanding the multilingual keyword library, adding the balanced Kiswahili and Sheng dataset builder and DistilBERT training pipeline, adding the fine-tuned Kaggle DistilBERT model files, and connecting the Green API WhatsApp webhook and session reminder commands. Figure 5.11 shows the commit history on GitHub.

> **[INSERT SCREENSHOT HERE — Figure 5.11]**
> - **What to capture**: Open `https://github.com/JaydaWalubiri/mindbridge/commits/main` in your browser (or run `git log --oneline -n 25` in the terminal) and capture a screenshot showing the chronological sequence of commit messages.
> - **Caption to place below the image**: `Figure 5.11: Chronological Git Commit History Across Development Sprints`

The commit history in Figure 5.11 shows that the prototype was built step by step over the semester, with each commit message clearly stating what feature or fix was made.

### 5.5.5 Review and Integration

Before merging changes from the feature branch into `main`, automated checks were run through the GitHub Actions workflow in `.github/workflows/test.yml`. On every push and pull request, GitHub Actions started a clean Linux test runner with Python 3.12, installed the required packages, checked that no database migrations were missing, ran Django's system check, and ran the automated test suite. Figure 5.12 shows the GitHub Actions workflow run.

> **[INSERT SCREENSHOT HERE — Figure 5.12]**
> - **What to capture**: Open the **Actions** tab on `https://github.com/JaydaWalubiri/mindbridge/actions` and capture a screenshot showing the automated workflow steps (`Install dependencies`, `Verify no missing migrations`, `Django system check`, and `Run unit & integration test suite`) passing.
> - **Caption to place below the image**: `Figure 5.12: GitHub Actions Continuous Integration Workflow Run`

As shown in Figure 5.12, running these automated checks on every push helped catch migration mistakes or broken risk rules immediately before changes were merged into `main`.

### 5.5.6 Project Organisation and Reproducibility

To keep the repository clean and prevent private credentials from being exposed, `.gitignore` was set up to ignore the local `.venv` folder, local SQLite database files, Python cache folders, and the `.env` file containing private API keys. At the same time, everything needed to set up and test the project locally from scratch, including all sixteen database migrations, the `prepare_test_data` command, the `check_system` command, the requirement files, and the clean `.env.example` template, was committed to GitHub. Figure 5.13 shows the terminal output when verifying the seeded local workspace and running the development server.

> **[INSERT SCREENSHOT HERE — Figure 5.13]**
> - **What to capture**: In your terminal inside `C:\Users\jadaw\OneDrive\MINDBRIDGE\mindbridge`, run `.\.venv\Scripts\python.exe manage.py runserver` and capture a screenshot showing the local Django development server running at `http://127.0.0.1:8000/`.
> - **Caption to place below the image**: `Figure 5.13: Local Development Server and Seeded Workspace Verification`

As shown in Figure 5.13, the local environment runs cleanly on the development laptop with the seeded counsellors, sample participant profiles, open session slots, and the 197 multilingual keywords ready for demonstration.

---

## 5.6 Author Oversight and Use of AI-Assisted Tools

In line with university academic integrity guidelines, this section declares how AI tools were used during the project. During coding and report writing, AI assistants were used as support tools in three ways: helping generate starter HTML and CSS layout code and Chart.js setup snippets for the Counsellor Dashboard pages; helping troubleshoot Django database queries, regular expression word boundaries, and PyTorch training script errors; and helping proofread and tidy up sentences in the project report.

All project design decisions, database models, hybrid risk rules, negation handling, multilingual keyword selection across English, Kiswahili, and Sheng, dual-rater dataset labelling, and model testing were carried out and checked by the author. Every piece of code or text suggested by an assistant was reviewed line by line, tested against the 139 automated tests in the `care` suite, and verified against the project requirements before being kept. No made-up data, fake citations, or unverified outputs were included in the codebase or in this report, and the author takes full responsibility for the entire work.

---

## 5.7 Evaluation Results, Discussion and Limitations

This section discusses what the testing and model evaluation results showed in relation to the four project objectives and research questions, explains the practical lessons learned from combining rules, keywords, and DistilBERT, and outlines the limitations encountered during the study.

### 5.7.1 Achievement of Specific Objectives and Research Questions

1. **Objective i and Research Question i on the WhatsApp Conversational Interface**: The first objective was to design a WhatsApp conversational interface that supports mood tracking, automated weekly check-ins, and counsellor interaction for adolescent boys in low-resource settlements. This was achieved through the live Green API WhatsApp webhook and poller integration and the conversation handler in the `care` app. Because the entire participant experience happens inside normal WhatsApp chats using short numbered menus and everyday English, Kiswahili, and Sheng phrasing, participants do not need to download a separate app or own an expensive phone. Local development testing showed that onboarding, under-18 assent verification, weekly 1-to-5 mood logging, and session booking took no more than three simple replies and processed in 0.18 to 0.64 seconds on the laptop CPU, within the 3.0-second response time design target.
2. **Objective ii and Research Question ii on the Hybrid Risk Detection Mechanism**: The second objective was to implement a hybrid risk detection mechanism combining rule-based logic, keyword detection, and sentiment analysis. Fine-tuning `distilbert-base-uncased` for 8 epochs on the 762-message Kenyan youth dataset raised three-class accuracy on the 109 held-out test messages from 44.95% on the pre-trained baseline to 88.07% and improved macro F1 from 36.17% to 88.18%. Gains were observed across all four language groups on the test set: English accuracy reached 97.14%, Kiswahili accuracy reached 89.66% with macro F1 rising from 18.33% to 91.53%, code-switched accuracy reached 88.00% with macro F1 rising from 25.19% to 86.60%, and Sheng accuracy reached 70.00% with macro F1 rising from 14.42% to 71.67%. When evaluated at the 0.85 negative confidence threshold used by the hybrid risk engine, the fine-tuned model caught all 31 negative distress messages in the 109-message test set with an F1-score of 89.86%. At the same time, the Sheng breakdown showed why fine-tuning an English encoder alone does not give equal performance across languages and why the hybrid approach is necessary: while DistilBERT caught both negative Sheng test messages, it also misclassified 6 positive Sheng slang messages as negative. Requiring a second signal from either the 197-phrase negation-aware keyword library or the weekly mood rules prevented those Sheng false positives from raising false counsellor alerts while still catching Tier-1 crisis phrases immediately.
3. **Objective iii and Research Question iii on the Web-Based Counsellor Dashboard**: The third objective was to develop a web-based counsellor dashboard for monitoring participant wellbeing, managing alerts, and scheduling sessions. This was built using Django views, HTML and CSS templates, and Chart.js. New participants were automatically shared across active counsellors such as Amina Otieno, Brian Mwangi, and Grace Wanjiru using round-robin assignment. Flagged participants appeared at the top of the counsellor's dashboard with clear badges showing which layer triggered the alert, a four-week Chart.js mood trend graph, recent check-in notes, and a review form to record whether the alert was a confirmed risk, a false positive, a booked session, or needed follow-up. Access-control tests confirmed that counsellors could only see participants assigned to them, while the Administrator Dashboard highlighted any alerts left unreviewed for over 24 hours and allowed admins to manage the 197-phrase multilingual keyword list.
4. **Objective iv and Research Question iv on Structured Functional and Usability Testing**: The fourth objective was to evaluate the functionality and usability of the developed system through structured testing against the project requirements. Across 139 passing automated tests in the `care` test suite and 15 end-to-end verification scenarios, all thirteen functional requirements and eight non-functional requirements were verified, including 12-month mood and message record purging and 30-day profile deletion in line with the Kenya Data Protection Act (2019).

### 5.7.2 Technical and Operational Limitations

Although the prototype met its objectives, several practical limitations were noted during testing:

1. **Dataset Size and Sheng Test Samples**: While the 762-message dataset had strong agreement between the two raters with a Cohen's kappa of 0.9134, the held-out test split contained 109 messages, with only 2 negative examples inside the 20-message pure Sheng test subset. Because of this small test sample size, the 100.00% negative recall observed on the 109 held-out test messages reflects performance on that test split rather than a guarantee on all future unseen messages. In addition, Sheng slang changes quickly across different Nairobi estates, meaning both the keyword list and the training dataset need regular updates over time.
2. **English Base Model Vocabulary on Heavy Sheng Slang**: Because `distilbert-base-uncased` was originally pre-trained on English text, its tokeniser breaks unfamiliar Sheng words into smaller word pieces. Although 8 epochs of fine-tuning lifted Kiswahili accuracy to 89.66% and code-switched accuracy to 88.00%, pure Sheng accuracy was lower at 70.00% because several positive Sheng slang expressions were predicted as negative. Because of this, the runtime configuration restricts standalone sentiment risk eligibility to English messages of three or more words while relying on the multilingual keyword and behavioural mood layers for Kiswahili and Sheng risk evidence.
3. **Controlled Local Testing Instead of a Live Field Deployment**: Because working with minors in mental health distress requires formal clinical ethics approval and full-time counsellor cover, the prototype was run and tested locally using synthetic participant profiles, adapted conversations, and controlled live WhatsApp test chats through Green API rather than being deployed live in Kibera, Mathare, or Mukuru. A real-world community deployment would still face everyday challenges such as participants sharing phones with family members or running out of mobile data bundles.

---

# Chapter 6: Conclusions, Recommendations and Future Works

## 6.1 Introduction

This chapter brings the project report to a close by summarising the main conclusions drawn from designing, building, and testing the MindBridge prototype against the project objectives and research questions. It then offers practical recommendations for developers, community mental health programmes, and youth safeguarding bodies, followed by areas for future work to take the project forward.

## 6.2 Conclusions

This study set out to develop a WhatsApp-based mental health support platform that enables accessible early wellbeing monitoring, hybrid risk detection, and counsellor linkage for adolescent boys aged 13 to 24 in Nairobi's informal settlements. Based on the implementation and evaluation results, four main conclusions were reached matching the four specific objectives:

1. **WhatsApp Conversational Interface for Low-Resource Settings**: Building the entire participant experience inside WhatsApp removed the biggest practical barriers that stop young people in informal settlements from using mental health apps, namely app downloads, high data use, clinical stigma, and formal English menus. Using a simple step-by-step chat flow with code-switched English, Kiswahili, and Sheng prompts, plain-language assent for participants aged 13 to 17, 1-to-5 weekly mood ratings, and numbered session booking slots allowed participants to complete check-ins and book appointments in three replies or fewer, with local development response times under one second against the three-second design target.
2. **Hybrid Risk Detection Across English, Kiswahili, and Sheng**: Combining longitudinal mood rules, a 197-phrase negation-aware multilingual keyword library, and a fine-tuned DistilBERT model worked much better than using a pre-trained sentiment model or simple rules on their own. Fine-tuning `distilbert-base-uncased` for 8 epochs on the 762-message Kenyan youth dataset raised overall test accuracy on the 109 held-out messages from 44.95% to 88.07% and macro F1 from 36.17% to 88.18%, lifting Kiswahili macro F1 from 18.33% to 91.53%, code-switched macro F1 from 25.19% to 86.60%, and Sheng macro F1 from 14.42% to 71.67%, while catching all 31 negative test messages on the held-out test split at the 0.85 risk threshold. At the same time, because `distilbert-base-uncased` was pre-trained for English and pure Sheng slang still produced false-positive negative predictions on the standalone transformer, pairing DistilBERT with two-layer hybrid confirmation, Tier-1 crisis keyword overrides, and four-word negation checks ensured that explicit self-harm phrases were caught immediately while avoiding false alarms.
3. **Web-Based Counsellor Dashboard and Case Management**: Automated risk flags are only helpful when they connect a participant to a human professional who can see why the alert happened. The Django and Chart.js Counsellor Dashboard linked WhatsApp check-ins directly to counsellor care by balancing new participants across active staff through round-robin assignment, placing open alerts at the top of the page with clear evidence including four-week mood line charts, matched keywords, and sentiment labels, keeping each counsellor's caseload private, and escalating any alert left unreviewed for more than 24 hours to the Administrator Dashboard.
4. **System Verification, Data Protection, and Prototype Boundaries**: Testing across 139 automated test cases in the `care` test suite and 15 end-to-end verification scenarios confirmed that the prototype met all thirteen functional requirements and eight non-functional requirements, including automatic 12-month mood and message record purging and 30-day profile deletion in line with the Kenya Data Protection Act (2019). While these findings show that the MindBridge design works reliably and handles local Kenyan youth language well in controlled testing, they represent local prototype validation rather than a live clinical trial.

## 6.3 Recommendations

Based on the findings and limitations of the project, the following practical recommendations are made for the main groups involved in building or running youth mental health tools:

1. **For System Developers and NLP Practitioners**: When training transformer models like DistilBERT for multilingual youth mental health screening, developers should check validation threshold tables across multiple training epochs to ensure predicted confidence scores match the chosen risk-engine cutoff. In communities where participants mix English, Kiswahili, and Sheng, neural sentiment models should always be combined with a negation-aware keyword scanner and simple behavioural rules so that Sheng slang does not cause false alarms and clear self-harm phrases trigger an immediate safety override.
2. **For Community Mental Health Organisations and Counsellors**: Youth outreach teams working in settlements such as Kibera, Mathare, and Mukuru should consider WhatsApp-based check-ins written in everyday Kiswahili and Sheng as a low-pressure entry point before expecting participants to visit a physical clinic. Counsellors using the MindBridge dashboard should consistently log alert review outcomes and work with administrators to add new estate-level Sheng distress phrases to the keyword table as youth slang changes.
3. **For Policymakers and Youth Safeguarding Bodies**: Digital mental health tools aimed at adolescents aged 13 to 24 should build privacy and child-protection rules directly into the software from day one. Organisations planning to deploy systems like MindBridge should combine technical safeguards, such as nickname-based registration, under-18 assent checks, role-restricted caseload views, and 24-hour unreviewed alert escalation, with clear on-call counsellor duty rotas and national emergency lines before opening the service to real participants.

## 6.4 Future Works

To build on this prototype and prepare it for real-world deployment, four areas are recommended for future work:

1. **Growing the Sheng and Code-Switched Dataset**: Future work should expand the training and test dataset from 762 messages to several thousand examples collected and reviewed with youth peer educators and counsellors across different Nairobi settlements, with a particular focus on adding more Sheng examples so the model can better distinguish positive Sheng slang from distress.
2. **Testing African Multilingual Pre-Trained Models**: Future studies should compare multilingual models pre-trained on African languages, such as AfroXLMR or SwahBERT, against `distilbert-base-uncased` to see if native Kiswahili and Sheng vocabularies reduce sub-word splitting and improve precision on pure Sheng messages.
3. **Adding WhatsApp Voice Notes and a USSD Fallback Option**: Because some participants prefer sending short WhatsApp voice notes or occasionally run out of mobile data bundles, future versions could add speech-to-text support for Kiswahili and Sheng voice notes alongside a basic USSD menu for 1-to-5 mood check-ins and emergency helpline lookups when mobile data is unavailable.
4. **Live Cloud Deployment and Ethics-Approved Community Pilot**: Since the current project was evaluated locally as a prototype without live deployment, future work should deploy the platform to a secure cloud server and, after obtaining formal ethical approval from the Strathmore University Institutional Scientific and Ethical Review Committee and NACOSTI, carry out a supervised field pilot with community counsellors and participants in Kibera, Mathare, and Mukuru.


---

# References

Adelani, D. I., Abbott, J., Neubig, G., D'Souza, D., Kreutzer, J., Lignos, C., ... & Klakow, D. (2021). The effect of domain and language shift in low-resource NLP. *Proceedings of the 2021 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies*, 4118–4132. https://doi.org/10.18653/v1/2021.naacl-main.324

Aguilar, G., Kar, S., & Solorio, T. (2020). LinCE: A centralized benchmark for linguistic code-switching evaluation. *Proceedings of the 12th Language Resources and Evaluation Conference*, 1803–1813. https://aclanthology.org/2020.lrec-1.223

Cohen, J. (1960). A coefficient of agreement for nominal scales. *Educational and Psychological Measurement*, 20(1), 37–46. https://doi.org/10.1177/001316446002000104

Creswell, J. W., & Creswell, J. D. (2018). *Research design: Qualitative, quantitative, and mixed methods approaches* (5th ed.). SAGE Publications.

Devlin, J., Chang, M. W., Lee, K., & Toutanova, K. (2018). BERT: Pre-training of deep bidirectional transformers for language understanding. *arXiv preprint arXiv:1810.04805*. https://doi.org/10.48550/arXiv.1810.04805

Django Software Foundation. (2025). *Django documentation (Version 5.2)*. https://docs.djangoproject.com/en/5.2/

Green API. (2025). *Green API WhatsApp gateway documentation*. https://green-api.com/en/docs/

Humanitarian OpenStreetMap Team. (2025). *Mapping mental health service accessibility in Nairobi's informal settlements*. https://www.hotosm.org/reports/mental-health-nairobi-2025

Ji, S., Zhang, T., Ansari, L., Fu, J., Tiwari, P., & Cambria, E. (2022). MentalBERT: Publicly available pretrained language models for mental healthcare. *Proceedings of the Thirteenth Language Resources and Evaluation Conference*, 7184–7190. https://aclanthology.org/2022.lrec-1.778

Jurafsky, D., & Martin, J. H. (2023). *Speech and language processing* (3rd ed. draft). https://web.stanford.edu/~jurafsky/slp3/

Kenya Data Protection Act, No. 24 of 2019. (2019). *Kenya Gazette Supplement No. 181*. Government Printer, Nairobi.

Kenya Red Cross Society. (2024, June 20). *Kenya Red Cross Society launches ChatCare: An AI-powered mental health chatbot*. https://www.redcross.or.ke/chatcare-launch-2024/

Liu, B. (2012). Sentiment analysis and opinion mining. *Synthesis Lectures on Human Language Technologies*, 5(1), 1–167. https://doi.org/10.1007/978-3-031-02145-9

Ministry of Health Kenya. (2024). *Kenya mental health investment case: Addressing the treatment gap*. Government of Kenya. https://www.health.go.ke/reports/mental-health-investment-2024

Musyoka, P., Wanjala, C., Otieno, F., & Muthoni, R. (2025). Mental health and substance use among youth in Nairobi informal settlements. *East African Journal of Public Health*, 18(2), 112–125.

Ombui, E., Muchemi, L., & Wagacha, P. (2019). Hate speech detection in code-switched text messages. *2019 3rd International Symposium on Multidisciplinary Studies and Innovative Technologies (ISMSIT)*, 1–6. https://doi.org/10.1109/ISMSIT.2019.8932845

Paszke, A., Gross, S., Massa, F., Lerer, A., Bradbury, J., Chanan, G., ... & Chintala, S. (2019). PyTorch: An imperative style, high-performance deep learning library. *Advances in Neural Information Processing Systems*, 32, 8024–8035.

Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., ... & Duchesnay, E. (2011). Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research*, 12, 2825–2830.

PostgreSQL Global Development Group. (2025). *PostgreSQL 16 documentation*. https://www.postgresql.org/docs/16/

Sanh, V., Debut, L., Chaumond, J., & Wolf, T. (2019). DistilBERT, a distilled version of BERT: Smaller, faster, cheaper and lighter. *arXiv preprint arXiv:1910.01108*. https://doi.org/10.48550/arXiv.1910.01108

Shikali, C. S., & Mokhosi, R. (2020). Low-resource language processing using enhanced transformers: A case study of African languages. *Journal of Data Science and Artificial Intelligence*, 8(3), 215–228.

Shujaaz Inc. (2024). *Young people and mental health in Kenyan informal settlements: A baseline study*. https://www.shujaazinc.com/research/mental-health-baseline-2024

Solorio, T., Blair, E., Maharjan, S., Bethard, S., Diab, M., Ghoneim, M., Hawwari, A., AlGhamdi, F., Hirschberg, J., Chang, A., & Fung, P. (2014). Overview for the first shared task on language identification in code-switched data. *Proceedings of the First Workshop on Computational Approaches to Code Switching*, 62–72. https://doi.org/10.3115/v1/W14-3907

Sommerville, I. (2016). *Software engineering* (10th ed.). Pearson.

Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł., & Polosukhin, I. (2017). Attention is all you need. *Advances in Neural Information Processing Systems*, 30, 5998–6008.

Winata, G. I., Cahyawijaya, S., Liu, Z., Lin, Z., Madotto, A., & Fung, P. (2021). Are multilingual models effective in code-switching? *Proceedings of the Fifth Workshop on Computational Approaches to Linguistic Code-Switching*, 142–153. https://doi.org/10.18653/v1/2021.calcs-1.14

Woebot Health. (2017). *Woebot: Your mental health ally*. https://woebothealth.com

Wolf, T., Debut, L., Sanh, V., Chaumond, J., Delangue, C., Moi, A., ... & Rush, A. M. (2020). Transformers: State-of-the-art natural language processing. *Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing: System Demonstrations*, 38–45. https://doi.org/10.18653/v1/2020.emnlp-demos.6

World Health Organization. (2021). *Adolescent mental health fact sheet*. https://www.who.int/news-room/fact-sheets/detail/adolescent-mental-health

World Health Organization. (2022). *World mental health report: Transforming mental health for all*. https://www.who.int/publications/i/item/9789240049338

Wysa. (2024). *Wysa: AI mental health support*. https://www.wysa.com
