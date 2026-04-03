# Tasks — Web Scraping & API REST
**Course:** Python Programming
**Total Score:** 20 points (10 pts each task)

---

# 🕷️ Task 1: Web Scraping — UNMSM Admission Exam Results
**Score:** 10 points

## Description
The goal of this task is to automatically extract the admission exam results
from Universidad Nacional Mayor de San Marcos using Python and Selenium,
career by career, and consolidate all the information into an Excel file.

---

## 🗂️ Expected Repository Structure

Create a repository named exactly **`Scraping_data`** with the following structure:

```
Scraping_data/
│
├── scraper.py                        # Main extraction script
├── README.md                         # Project explanation
├── output/
│   └── resultados_sanmarcos.xlsx     # Consolidated Excel with all results
└── video/
    └── link.txt                      # Link to your explanatory video
```

Place the link to your repository and video here:
https://docs.google.com/spreadsheets/d/16i_gtlZV08QARXl8FM5yX503XjDyKPiRFRbo56cjR2k/edit?usp=sharing

---

### 🔧 The script must:
- Access: `https://admision.unmsm.edu.pe/Website20262/A/A.html`
- Automatically extract the links of **all careers**
- Iterate career by career extracting **all applicants** (not just the first 50)
- Save the result in a **consolidated Excel file** inside the `output/` folder

### 💡 Important tips based on the San Marcos page:

**1. The table uses DataTables (JavaScript pagination)**
The page loads all the data into memory but only displays 50 records by default.
You need to find a way to solve this challenge.

---

## 🌿 GitHub Workflow (MANDATORY)

- ❌ **Do not work directly on `main`** — points will be deducted
- ✅ Create a working branch
- ✅ Make progressive commits with descriptive messages
- ✅ When finished, merge into `main` via a **Pull Request**

---

## 📹 Explanatory Video (2.5 points)

- Duration: **3 minutes maximum**
- Must show:
  - Brief explanation of the code
  - The script running live
  - The final Excel file with the extracted data
- Upload the link in the file `video/link.txt`

---

## 📝 README.md

Must include at least:
- What does the project do?
- How to install the dependencies?
- How to run the script?
- What does the output contain?

---

## 🏆 Grading Rubric — Task 1 (0 - 10 pts)

| Criteria | Points |
|---|---|
| Script works and correctly extracts all careers | 2.5 pts |
| Explanatory video (3 min, shows code and output) | 2.5 pts |
| Branch workflow + merge via Pull Request | 1.5 pts |
| Complete consolidated Excel in `output/` folder | 1.5 pts |
| Explanatory `README.md` | 1.0 pt |
| Progressive commits with descriptive messages | 0.5 pt |
| Error handling in the code (`try/except`) | 0.5 pt |
| **TOTAL** | **10 pts** |

> ⚠️ **Penalty:** If you are found to have worked directly on `main`
> without using branches, **1.5 points will be automatically deducted**.

---

# 🎮 Task 2: API REST — RAWG Video Games Database
**Score:** 10 points

## Description
The goal of this task is to consume the RAWG API to extract, analyze,
and compare video game data using Python.
You will create a new notebook inside the **same repository** `Scraping_data`.

---

## 🗂️ Expected Repository Structure

Add the following to your existing **`Scraping_data`** repository:

```
Scraping_data/
│
├── scraper.py                        # (Task 1 — already exists)
├── README.md                         # Update with the API section
│
├── api/
│   ├── tarea_rawg_api.ipynb          # Main task notebook
│   └── output/
│       └── top20_rawg.csv            # CSV file generated in the task
```

---

## 🔑 Step 1 — Get your RAWG API Key

1. Go to **https://rawg.io** and create your account
2. Visit **https://rawg.io/apidocs**
3. Click **Get API Key** and fill out the form:

| Field | What to enter |
|---|---|
| Site/App URL | `https://localhost` |
| Description | `API Python Class` |

4. Copy your API Key and paste it into your notebook

> ⚠️ Do not upload your API Key to GitHub. Store it in a local variable.

---

## 📓 Notebook Structure

Each section must have **Markdown cells** explaining what you are doing
and **code cells** with the output executed and visible.

---

## 🟢 Part A — General Exploration &nbsp;&nbsp;&nbsp; *(2 pts)*

### A1 — *(1 pt)*
How many games does RAWG have registered in total?
Print the number with a clear message.
> Hint: the `count` field is in the response from the `/games` endpoint.

---

## 🔵 Part B — Category Analysis &nbsp;&nbsp;&nbsp; *(2 pts)*

### B1 — *(1 pt)*
What is the **top 5 highest rated games** of all time according to Metacritic?
Show: name, rating, and metacritic score.

### B2 — *(1 pt)*
What are the **10 best games available on Steam** (store_id=1)?
Show name, rating, and metacritic score.

---

## 🟡 Part C — Comparisons &nbsp;&nbsp;&nbsp; *(3 pts)*

### C1 — *(0.5 pts)*
Compare the **top 5 games on PC** (platform_id=4) vs **top 5 on PS5** (platform_id=187).
Which platform has the highest rated games?

### C2 — *(0.5 pts)*
Choose **3 famous games** and build a comparison table with:
name, rating, metacritic, genres, and platforms.

### C3 — *(0.5 pts)*
Query the top 5 games from at least **4 different genres**, calculate the
**average rating** for each, and determine which genre produces
the best games according to users.

### C4 — *(0.5 pts)*
Compare the best games from **3 different years** of your choice.
In which year were the games with the highest average metacritic score released?

### C5 — *(1.0 pt)*
Export the **top 20 games of all time** to a CSV file named
`top20_rawg.csv` inside the `api/output/` folder.

The CSV must have the following columns:
`name, rating, metacritic, release_date, main_genre`

Display the first 5 rows of the generated file in the notebook.

---

## 🔴 Part D — Insights & Conclusions &nbsp;&nbsp;&nbsp; *(3 pts)*

### D1 — *(1.0 pt)*
In a Markdown cell write your **personal conclusions** answering:

- What was the most interesting thing you found in the data?
- Which genre or platform surprised you the most and why?
- What other question would you ask this API if you had more time?
- How many requests did you use in total? (call `client.resumen_requests()`)

> This question is graded on the **depth of your analysis**,
> not on having a "correct" answer.

---

## 🌿 GitHub Workflow (MANDATORY — same rules as Task 1)

- ❌ **Do not work directly on `main`**
- ✅ Create a branch for this task (e.g. `feature/api-rawg`)
- ✅ Progressive commits with descriptive messages
- ✅ Merge into `main` via a **Pull Request**

---

## 🏆 Grading Rubric — Task 2 (0 - 10 pts)

| Criteria | Points |
|---|---|
| Part A — General Exploration | 2.0 pts |
| Part B — Category Analysis | 2.0 pts |
| Part C — Comparisons + CSV exported | 3.0 pts |
| Part D — Insights + personal conclusions | 3.0 pts |
| **TOTAL** | **10 pts** |

> ⚠️ **Penalty:** Working directly on `main` deducts **3 points**.
> Code cells without visible output deduct **0.5 points per cell**.

---

## ✅ Checklist before submitting

- [ ] The notebook is named `tarea_rawg_api.ipynb` and is inside the `api/` folder
- [ ] The file `top20_rawg.csv` is inside `api/output/`
- [ ] All code cells are executed with visible output
- [ ] The code is commented
- [ ] You used a branch + Pull Request for the merge
- [ ] The `README.md` mentions both tasks

---

## 📊 Global Score Summary

| Task | Description | Score |
|---|---|---|
| Task 1 | Web Scraping — UNMSM | 10 pts |
| Task 2 | API REST — RAWG | 10 pts |
| **Course Total** | | **20 pts** |

---

## 📅 Deadline
**Friday, April 10 — 11:59 PM**
Submit the link to your repository in the same Google Sheets form.

> 💬 Any questions, reach out on Discord. Good luck! 🎮
