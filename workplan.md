# Veil Roadmap & Workplan

Dokumen ini adalah versi terbaru dari workplan yang sudah diperbarui dengan status proyek saat ini, termasuk refactoring yang baru dilakukan, dan roadmap baru yang fokus pada pengalaman "human-like AI".

---

## Current State

| Area | Status | Notes |
|---|---|---|
| **Core Architecture** | OK | Stabil setelah rewrite Phase 5. |
| Emotional State (5-dim + decay) | OK | `personality/state.py` |
| Emotional Memory | OK | `memory/emotional.py` (sekarang pakai `JSONStore`) |
| Persistence + Schema Migration | OK | `personality/persistence.py` (sekarang pakai `JSONStore`) |
| Initiative & Inactivity | OK | `personality/initiative.py`, `personality/inactivity.py` |
| Rhythm & Reaction Layer | OK | `personality/rhythm.py` |
| Emotional Modes (6 modes, decay) | OK | `personality/core.py` |
| **Cognition & Tools** | OK | |
| Invisible Search Cognition | OK | `core/cognition.py` |
| Tool Routing | OK | `core/orchestrator.py` (termasuk `is_..._query` functions) |
| Tool Resilience (with_retry) | OK | `utils/async_utils.py` |
| **Memory** | OK | |
| Scoring-based Recall (LTM) | OK | `memory/long_term.py` |
| Short-Term Memory (STM) | OK | `memory/short_term.py` |
| **User Interface** | OK | |
| CLI + TUI Entry Points | OK | `app.py`, `app_tui.py` |
| **Utilities** | OK | |
| Structured Logging | OK | `utils/logger.py` (sekarang pakai `RichHandler`) |
| Text Sanitization | OK | `utils/text.py` (baru, sentralisasi) |
| **Testing** | PARTIAL | 44/45 passing (1 expected LLM-dependent failure) |

---

## Future Roadmap: Human-like AI

Tujuan utama: Membuat AI terasa seperti manusia.

### Phase 6 -- Foundation Upgrade (Quick Wins)

Tujuan: Meningkatkan fondasi inti untuk mendukung pengalaman yang lebih mirip manusia.

| Feature | Description | Status | Priority |
|---|---|---|---|
| **Context Window Full Utilization** | Memanfaatkan kapasitas penuh `n_ctx` model (32k) untuk pemahaman konteks jangka panjang yang lebih baik. | NOT STARTED | High |
| **User Profile Auto-Building** | Otomatis mengekstrak dan menyimpan profil terstruktur user (hobi, pekerjaan, preferensi, dll.) dari percakapan. | NOT STARTED | Medium |
| **Semantic Memory Retrieval** | Mengganti sistem pencarian memori berbasis keyword dengan metode semantik (e.g., embeddings) untuk recall yang lebih relevan. | NOT STARTED | Medium |
| **Personality Drift Engine** | Mengembangkan sistem agar trait kepribadian Stella (humor, warmth, dll.) dapat beradaptasi dan berubah secara halus berdasarkan interaksi. | NOT STARTED | Medium |
| **Implicit & Explicit Feedback Loop** | Memungkinkan user memberi rating respons dan Stella secara otomatis belajar dari reaksi user. | NOT STARTED | Medium |

### Phase 7 -- Voice & Presence

Tujuan: Memberikan Stella "suara" dan kehadiran yang lebih nyata.

| Feature | Description | Status | Priority |
|---|---|---|---|
| **Local TTS Integration** | Integrasi Text-to-Speech lokal (e.g., Piper, Coqui) agar Stella dapat merespons dengan suara. | NOT STARTED | High |
| **Speech Recognition** | Integrasi Speech-to-Text lokal (e.g., Whisper) untuk input suara dari user. | NOT STARTED | High |
| **Background Idle Chatter** | Saat tidak ada interaksi, Stella sesekali mengeluarkan komentar spontan (nguap, observasi) untuk menciptakan rasa kehadiran. | NOT STARTED | Medium |
| **Active Notification System** | Stella dapat memicu percakapan atau memberi notifikasi aktif berdasarkan informasi yang ia proses (selain dari inactivity). | NOT STARTED | Low |

### Phase 8 -- Desktop Companion & Environmental Awareness

Tujuan: Menjadikan Stella bagian dari lingkungan desktop user.

| Feature | Description | Status | Priority |
|---|---|---|---|
| **Desktop Overlay** | Antarmuka visual sederhana (e.g., floating window) untuk menampilkan avatar atau mood Stella di desktop. | NOT STARTED | Medium |
| **Screen Context Awareness** | Kemampuan untuk memproses screenshot periodik untuk memahami apa yang sedang user lihat/kerjakan. | NOT STARTED | Medium |
| **Mouse/Keyboard Observation** | Mendeteksi aktivitas user (idle vs. aktif) melalui input mouse/keyboard untuk interaksi yang lebih alami. | NOT STARTED | Low |
| **Basic Computer Control** | Stella dapat melakukan tugas-tugas sederhana di komputer (membuka aplikasi, mencari file, membaca clipboard). | NOT STARTED | Low |

### Phase 9 -- Autonomy & Advanced Adaptation

Tujuan: Membangun otonomi dan kemampuan adaptasi yang lebih kompleks.

| Feature | Description | Status | Priority |
|---|---|---|---|
| **Multi-threaded Conversation** | Stella dapat mengelola beberapa topik atau tugas secara bersamaan dalam satu percakapan. | NOT STARTED | Medium |
| **Adaptive Personality Calibration** | Fine-tune kepribadian secara dinamis berdasarkan interaksi jangka panjang dengan user. | NOT STARTED | Low |
| **Self-Improvement Loop** | Sistem di mana Stella dapat mengevaluasi kualitas responsnya sendiri dan belajar dari kesalahan. | NOT STARTED | Low |

### Phase 10 -- Platform Expansion & Visual Presence

Tujuan: Membawa Stella ke berbagai platform dan menambahkan aspek visual yang lebih kaya.

| Feature | Description | Status | Priority |
|---|---|---|---|
| **Discord/Telegram Integration** | Menjadikan Stella sebagai bot di platform chat populer. | NOT STARTED | Medium |
| **VRM/Live2D Avatar** | Integrasi avatar visual (2D/3D) untuk tampilan yang lebih menarik dan ekspresif. | NOT STARTED | Low |

---

## Technical Debt & Refinement Backlog

Daftar hal-hal yang perlu diperbaiki atau ditingkatkan secara teknis.

| Item | Description | Priority |
|---|---|---|
| **Fragile LLM Test** | Test `calculator via orch` di `test_agent.py` terlalu kaku dan sering gagal karena sifat model. Perlu diubah untuk memeriksa *intent* (apakah tool dipanggil) bukan output. | Medium |
| **Hardcoded CUDA Paths** | `_setup_cuda_paths()` di `llm/engine.py` kurang portabel. Cari cara yang lebih robust untuk mendeteksi path CUDA. | Low |
| **API Key Validation** | Tidak ada validasi untuk `TAVILY_API_KEY` saat startup. Tambahkan warning jika kosong. | Low |
| **`with_retry` Utility** | `utils/async_utils.py` adalah implementasi custom. Pertimbangkan untuk menggantinya dengan library standar seperti `tenacity` jika kebutuhan retry menjadi lebih kompleks. | Very Low |
| **Cache TTL Logic** | `_CachedMixin` di `tools/web/search.py` adalah implementasi custom. Jika butuh cache yang lebih canggih, pertimbangkan `cachetools` (membutuhkan dependensi baru). | Very Low |

---

## Refactoring & Cleanup Log 

- **DELETED**: `vision/` directory (semua file stub).
- **DELETED**: `tools/registry.py` (legacy code).
- **DELETED**: `core/setup.py` (digantikan `core/bootstrap.py`).
- **REFACTORED**: `app.py` & `app_tui.py` sekarang menggunakan `core/bootstrap.py` untuk startup.
- **REFACTORED**: `memory/emotional.py` & `personality/persistence.py` sekarang menggunakan `memory.store.JSONStore` untuk file I/O.
- **REFACTORED**: `utils/logger.py` sekarang menggunakan `rich.logging.RichHandler` untuk output console.
- **CREATED**: `utils/text.py` untuk sentralisasi `sanitize_llm_output`.
- **MOVED**: Logic `is_..._query` dari `personality/core.py` ke `core/orchestrator.py`.

---

## Archived Phases

- **Phase 2: Agentification**
- **Phase 3: Proto-Agent**
- **Phase 4: Overengineering Era**

(Detail dari fase-fase ini bisa dilihat di versi lama workplan jika dibutuhkan, tapi sudah dihapus dari dokumen ini untuk kejelasan.)
