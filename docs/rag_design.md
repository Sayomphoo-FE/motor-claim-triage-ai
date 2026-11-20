# RAG Design — Motor Insurance Claim Triage

> เอกสารนี้อธิบายการออกแบบ Retrieval-Augmented Generation (RAG)
> ในโปรเจค Motor Insurance Claim Triage ตั้งแต่การแบ่ง chunk ไปจนถึงการ retrieve
> และเหตุผลที่เลือกแนวทางนี้

---

## ภาพรวม

ระบบ RAG มีเป้าหมายเดียว: **ให้ Claude เห็นเฉพาะ clause ที่เกี่ยวข้อง** กับ claim แต่ละเคส
แทนที่จะให้ policy ทั้งหมดเข้า context ทุกครั้ง

```
motor_policy.md ──→ parse ──→ embed ──→ Qdrant
                                           │
claim description ──→ 4 queries ──→ retrieve top-3 × 4
                                           │
                               ~10 unique clauses ──→ Claude prompt
```

---

## 1. แหล่งข้อมูล

ไฟล์เดียว: `data/policies/motor_policy.md`

Policy ถูก format เป็น Markdown แบบมี heading ชัดเจน:

```markdown
## Section 2 — Exclusions

### Clause 2.2 — Illegal Racing

Damage arising from participation in illegal racing is not covered.
```

มีทั้งหมด **13 clauses** ใน 4 sections:

| Section | Clauses | ครอบคลุม |
|---|---|---|
| Section 1 | 1.1 | Covered Events (5 perils) |
| Section 2 | 2.1–2.5 | Exclusions |
| Section 3 | 3.1–3.3 | Required Documents |
| Section 4 | 4.1–4.4 | Routing Rules |

---

## 2. การแบ่ง Chunk

### กลยุทธ์: 1 Clause = 1 Chunk

ไม่ใช้ token-based chunking หรือ sliding window
เหตุผลคือ policy rules แต่ละ clause สั้น (97–277 chars) และมี "ความหมายเดียว"
การตัดกลาง clause จะทำให้ embedding ผสม context และ score ต่ำลง

### วิธี Parse (`app/rag/ingest.py`)

```python
SECTION_RE = re.compile(r"^## Section (\d+) — (.+)$")
CLAUSE_RE  = re.compile(r"^### Clause (\d+\.\d+) — (.+)$")
```

อ่าน markdown ทีละ line:

| line ที่พบ | action |
|---|---|
| `## Section X — ...` | บันทึก section metadata, reset buffer |
| `### Clause X.Y — ...` | flush chunk ที่ค้างอยู่, เริ่ม clause ใหม่ |
| บรรทัดทั่วไป (ถ้ามี clause active) | append เข้า buffer |
| จบไฟล์ | flush chunk สุดท้าย |

### รูปแบบ text ของแต่ละ chunk

```
[Clause 2.2 — Illegal Racing]
Damage arising from participation in illegal racing is not covered.
```

**สำคัญ:** ชื่อ clause ถูกใส่ไว้ใน `text` ด้วย (ไม่ใช่แค่ metadata)
เพราะ embedding model ต้องเห็น heading เพื่อให้รู้ว่า text นี้คือ rule ประเภทไหน

### Metadata ที่แนบกับทุก chunk

```python
{
    "clause_id":   "2.2",
    "section_num": "2",          # ← ใช้ filter ตอน retrieve
    "section":     "Exclusions",
    "title":       "Illegal Racing",
    "text":        "[Clause 2.2 — ...]\n...",
    "source":      "motor_policy.md",
}
```

`section_num` เป็น key สำคัญสำหรับ metadata filter ตอน retrieve

---

## 3. การ Embed

**Model:** `BAAI/bge-small-en-v1.5` ผ่าน FastEmbed

| property | ค่า |
|---|---|
| Dimensions | 384 |
| Distance metric | Cosine |
| Model size | ~33 MB |
| Hardware | CPU (ไม่ต้องการ GPU) |

> สำหรับ production ที่รองรับภาษาไทย ควรเปลี่ยนเป็น
> `intfloat/multilingual-e5-large` (1024-dim) แต่สำหรับ 13-clause
> English policy corpus ตัวนี้เพียงพอแล้ว

```python
embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
vectors = list(embedder.embed([c.text for c in chunks]))
# → list of 13 numpy arrays, each shape (384,)
```

---

## 4. การเก็บลง Qdrant

**Vector store:** Qdrant รันใน Docker (`docker-compose.yml`)

```python
# สร้าง collection ใหม่ทุกครั้ง (drop + recreate)
client.create_collection(
    collection_name="motor_policy",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
)

# upsert 13 points พร้อมกัน
points = [
    PointStruct(
        id=uuid5(NAMESPACE_DNS, f"motor_policy.md:{clause_id}"),  # deterministic
        vector=vec.tolist(),
        payload=chunk.payload(),
    )
    for chunk, vec in zip(chunks, vectors)
]
client.upsert(collection_name="motor_policy", points=points, wait=True)
```

**UUID เป็น deterministic** (จาก `source:clause_id`) ทำให้การ re-ingest ไม่สร้าง duplicate

แต่ละ point ใน Qdrant จึงมีโครงสร้าง:

```
Point {
  id:      "a3f2c1d4-..."    (UUID5)
  vector:  [0.12, -0.08, ...]  (384 floats, cosine-normalized)
  payload: { clause_id, section_num, section, title, text, source }
}
```

---

## 5. การ Retrieve ตอน Triage

### 4 Section-Specific Sub-Queries

จุดเด่นหลักของ RAG ใน project นี้คือ **ไม่ใช้ query เดียว**
แต่สร้าง 4 sub-queries แยกตาม section (`app/agents/triage.py`):

```python
def _generate_queries(description, history, documents):
    return [
        (f"Covered perils for: {description}",             section="1"),
        (f"Exclusions that might apply to: {description}. "
         f"History: {history}.",                            section="2"),
        (f"Required documents for this claim type. "
         f"Submitted: {documents}.",                        section="3"),
        (f"Routing rules for this claim situation: "
         f"{description}",                                  section="4"),
    ]
```

### ทำไมต้องแยก 4 queries?

ถ้าส่ง 1 query อาจได้ผลแบบนี้:
```
top-10 results: Clause 3.1, 3.2, 3.3, 3.1, 3.2, 3.3, 1.1, 3.1, ...
→ ไม่มี exclusion เลย → Claude ไม่เห็น Clause 2.2 (Illegal Racing)
```

การ filter ต่อ section **การันตีว่า Claude เห็น coverage + exclusion + documents + routing ครบ**

### ขั้นตอนการ Retrieve (`app/rag/retriever.py`)

สำหรับแต่ละ query:

```python
# 1. embed query
vector = next(iter(embedder.embed([query]))).tolist()

# 2. query Qdrant พร้อม section filter
hits = client.query_points(
    collection_name="motor_policy",
    query=vector,
    limit=3,                                    # top-3 per section
    query_filter=Filter(must=[
        FieldCondition(key="section_num", match=MatchValue(value=section_num))
    ]),
    with_payload=True,
)
```

### Deduplication — keep best score per clause

```python
seen: dict[str, RetrievedChunk] = {}
for query, section in queries:
    for hit in retrieve(query, top_k=3, section_num=section):
        prev = seen.get(hit.clause_id)
        if prev is None or hit.score > prev.score:
            seen[hit.clause_id] = hit

result = sorted(seen.values(), key=lambda c: c.score, reverse=True)
```

Clause เดียวกันอาจ relevant กับหลาย query เช่น Clause 3.1 โผล่ทั้ง query 3 และ query 1
Dedup เก็บแค่ score สูงสุด ป้องกัน Claude เห็น text ซ้ำ

### ตัวเลขสรุป

| | ค่า |
|---|---|
| Queries ต่อ 1 claim | 4 |
| top-k ต่อ query | 3 |
| Max hits ก่อน dedup | 12 |
| Unique chunks หลัง dedup (ทั่วไป) | 9–11 |
| Sections ที่ cover | 4/4 เสมอ |

---

## 6. Format ใน Prompt

Chunks ที่ได้จะถูก format เข้า prompt template แบบนี้:

```
[Clause 1.1] (section: Covered Events, score: 0.89)
[Clause 1.1 — Covered Perils]
The policy covers the following events: ...

---

[Clause 2.2] (section: Exclusions, score: 0.84)
[Clause 2.2 — Illegal Racing]
Damage arising from participation in illegal racing is not covered.

---

[Clause 3.1] (section: Required Documents, score: 0.77)
...
```

Claude จะได้เห็น score ด้วย ทำให้รู้ว่า clause ไหน "เกี่ยวข้องมากสุด"

---

## 7. Output Guardrail — Citation Verification

หลัง Claude ตอบกลับมา output guardrail ตรวจว่า clause ที่ Claude อ้างทุกตัว
**มีอยู่ใน retrieved set จริง**:

```python
retrieved_ids = {c.clause_id for c in retrieved}  # e.g. {"1.1", "2.2", "3.1", ...}

for clause_id in claude_cited_clauses:
    if clause_id not in retrieved_ids:
        # ลบออก + บันทึก trigger "citation_invalid:X.Y"
        strip(clause_id)
```

ถ้า Claude hallucinate Clause ที่ไม่ได้ retrieve → ถูกลบก่อนส่งให้ Officer
**Citation validity = 100% บน 6 test cases**

---

## 8. การ Deploy และ Re-ingest

```bash
# ครั้งแรก: start Qdrant
docker compose up -d

# ingest policy (รันครั้งเดียว หรือเมื่อ policy เปลี่ยน)
uv run python scripts/ingest_policy.py

# ผลลัพธ์:
# Ingested 13 chunks → collection motor_policy (384-dim cosine)
```

การ re-ingest ทุกครั้ง **drop + recreate** collection ทั้งหมด
เพราะ policy เปลี่ยนยาก และข้อมูลน้อยพอที่ full re-index ใช้เวลาไม่ถึง 1 วินาที

---

## 9. ข้อจำกัดและแนวทางปรับปรุง

| ข้อจำกัด | แนวทางแก้ใน Production |
|---|---|
| English-only embedding | เปลี่ยนเป็น `multilingual-e5-large` |
| Policy 1 ไฟล์ / 13 clauses | เพิ่ม multi-policy support + policy version tracking |
| top-k=3 fixed | ปรับตาม claim type (theft → เพิ่ม Section 2 weight) |
| Cosine similarity เท่ากัน | เพิ่ม BM25 hybrid search สำหรับ keyword ชัดเจน เช่น clause ID |
| Re-ingest = drop all | ใช้ versioned points + soft-delete |
| ไม่มี query expansion | เพิ่ม HyDE (Hypothetical Document Embeddings) สำหรับ short description |
