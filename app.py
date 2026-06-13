import json
import html
import random
import os
import sqlite3
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Quiz Demo", layout="wide")

APP_PASSWORD = "iuanh"

st.markdown(
    """
    <style>
    html {
        scroll-behavior: smooth;
    }

    .question-nav {
        width: 100%;
        max-height: calc(100vh - 7.25rem);
        overflow-y: auto;
        padding: 0.15rem 0.5rem 0.35rem 0;
    }

    .question-nav-title {
        margin: 0 0 1rem;
        font-size: 1.5rem;
        font-weight: 700;
        color: inherit;
    }

    .question-nav-grid {
        display: grid;
        grid-template-columns: repeat(5, minmax(2.75rem, 1fr));
        gap: 0.9rem;
    }

    .question-nav-item {
        display: flex;
        align-items: center;
        justify-content: center;
        aspect-ratio: 1 / 1;
        min-width: 2.75rem;
        border: 1px solid rgba(156, 163, 175, 0.45);
        border-radius: 0.5rem;
        background: rgba(17, 24, 39, 0.25);
        color: inherit !important;
        font-weight: 700;
        text-decoration: none !important;
        transition: background-color 120ms ease, border-color 120ms ease, transform 120ms ease;
    }

    .question-nav-item:hover {
        border-color: rgba(96, 165, 250, 0.9);
        transform: translateY(-1px);
    }

    .question-nav-item.answered {
        background: #2563eb;
        border-color: #60a5fa;
        color: #ffffff !important;
    }

    .question-nav-item.correct {
        background: #22c55e !important;
        border-color: #16a34a !important;
        color: #ffffff !important;
    }

    .question-nav-item.wrong {
        background: #ef4444 !important;
        border-color: #dc2626 !important;
        color: #ffffff !important;
    }

    .question-anchor {
        scroll-margin-top: 1rem;
    }

    @media (max-width: 900px) {
        .question-nav {
            max-height: 34vh;
            padding: 0.75rem 1rem;
            background: var(--background-color, rgb(14, 17, 23));
            border-bottom: 1px solid rgba(156, 163, 175, 0.2);
        }

        .question-nav-grid {
            grid-template-columns: repeat(8, minmax(2.25rem, 1fr));
            gap: 0.5rem;
        }

        .question-anchor {
            scroll-margin-top: 15rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def require_password():
    if st.session_state.get("authenticated"):
        return

    st.title("A TTQT nhíeeeee")
    st.markdown("### Nhập mật khẩu để vào app")

    with st.form("password_form"):
        password = st.text_input("Mật khẩu", type="password")
        submitted = st.form_submit_button("Vào app")

    if submitted:
        if password == APP_PASSWORD:
            st.session_state["authenticated"] = True
            st.session_state["is_admin"] = False
            st.rerun()
        elif password == "admin":
            st.session_state["authenticated"] = True
            st.session_state["is_admin"] = True
            st.rerun()
        else:
            st.error("Sai mật khẩu.")

    st.stop()


# ----------------- HÀM CHẤM ĐIỂM -----------------
def grade_exam(questions):
    detail_scores = []
    total_score = 0.0

    for i, q in enumerate(questions):
        q_type = q.get("type", "single")
        options = q["options"]
        explanations = q.get("explanations", [])
        correct = set(q["correct_answers"])  # danh sách index đáp án đúng
        q_id = q.get("id", i + 1)

        if q_type == "single":
            # radio trả về chính chuỗi option
            user_choice = st.session_state.get(f"q_{i}")
            if user_choice is None:
                score = 0.0
                user_indices = []
            else:
                user_idx = options.index(user_choice)
                user_indices = [user_idx]
                score = 1.0 if user_idx in correct else 0.0

        else:  # multiple
            selected_indices = []
            for j, _ in enumerate(options):
                if st.session_state.get(f"q_{i}_opt_{j}", False):
                    selected_indices.append(j)

            user_indices = selected_indices
            true_selected = len(correct.intersection(selected_indices))
            false_selected = len(set(selected_indices) - correct)

            # mỗi câu multiple tối đa 1 điểm
            if len(correct) > 0:
                raw = (true_selected - false_selected) / len(correct)
            else:
                raw = 0.0
            score = max(0.0, raw)

        total_score += score
        detail_scores.append(
            {
                "id": q_id,
                "question": q["question"],
                "type": q_type,
                "options": options,
                "explanations": explanations,
                "score": score,
                "user_indices": user_indices,
                "correct_indices": list(correct),
            }
        )

    return total_score, detail_scores


def clear_answers():
    # Xoá toàn bộ key q_* trong session_state khi load đề mới
    keys_to_delete = [k for k in st.session_state.keys() if k.startswith("q_")]
    for k in keys_to_delete:
        del st.session_state[k]
    if "last_result" in st.session_state:
        del st.session_state["last_result"]


def is_question_answered(idx, question):
    q_type = question.get("type", "single")

    if q_type == "single":
        return st.session_state.get(f"q_{idx}") is not None

    options = question.get("options", [])
    return any(st.session_state.get(f"q_{idx}_opt_{j}", False) for j, _ in enumerate(options))


def validate_questions(questions):
    assert isinstance(questions, list), "JSON phải là một list các câu hỏi."
    assert len(questions) > 0, "Danh sách câu hỏi không được để trống."

    for idx, q in enumerate(questions, start=1):
        assert isinstance(q, dict), f"Câu {idx} phải là một object."
        for field in ["question", "options", "correct_answers"]:
            assert field in q, f"Thiếu trường '{field}' trong câu {idx}."
        assert isinstance(q["options"], list) and q["options"], f"'options' của câu {idx} phải là list không rỗng."
        assert isinstance(q["correct_answers"], list), f"'correct_answers' của câu {idx} phải là list."


def load_questions_from_text(raw_text):
    questions = json.loads(raw_text)
    validate_questions(questions)
    st.session_state["questions"] = questions
    clear_answers()


def render_question_nav(questions):
    nav_items = []
    for idx, question in enumerate(questions):
        answered_class = " answered" if is_question_answered(idx, question) else ""
        label = html.escape(str(idx + 1))
        nav_items.append(
            f'<a class="question-nav-item{answered_class}" '
            f'href="#question-{idx + 1}" data-question-index="{idx}" '
            f'title="Question {idx + 1}">{label}</a>'
        )

    st.markdown(
        f"""
        <div id="question-nav-pin"></div>
        <div class="question-nav">
            <div class="question-nav-grid">
                {''.join(nav_items)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_result_question_nav(questions, detail_scores):
    nav_items = []
    for idx, (question, detail) in enumerate(zip(questions, detail_scores)):
        is_correct = detail['score'] == 1.0
        result_class = " correct" if is_correct else " wrong"
        label = html.escape(str(idx + 1))
        nav_items.append(
            f'<a class="question-nav-item{result_class}" '
            f'href="#question-{idx + 1}" data-question-index="{idx}" '
            f'title="Question {idx + 1}">{label}</a>'
        )

    st.markdown(
        f"""
        <div id="question-nav-pin"></div>
        <div class="question-nav">
            <div class="question-nav-grid">
                {''.join(nav_items)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def sync_question_nav_sticky():
    components.html(
        """
        <script>
        const doc = window.parent.document;
        const nav = doc.querySelector('.question-nav');
        if (nav) {
            let col = nav.closest('[data-testid="column"]');
            let row = nav.closest('[data-testid="stHorizontalBlock"]');
            if (!col && row) {
                let current = nav;
                while (current.parentElement && current.parentElement !== row) {
                    current = current.parentElement;
                }
                col = current;
            }
            if (col && row) {
                row.style.alignItems = 'stretch';
                col.style.position = 'sticky';
                col.style.alignSelf = 'flex-start';
                col.style.zIndex = '100';
                if (window.parent.innerWidth <= 900) {
                    col.style.top = '3.65rem';
                } else {
                    col.style.top = '7.25rem';
                }
            }
        }
        </script>
        """,
        height=0,
    )


def sync_question_nav_answer_state(question_count):
    components.html(
        f"""
        <script>
        const questionCount = {question_count};
        const doc = window.parent.document;

        function anchors() {{
            return Array.from({{ length: questionCount }}, (_, idx) =>
                doc.getElementById(`question-${{idx + 1}}`)
            ).filter(Boolean);
        }}

        function questionForInput(input, markers) {{
            let current = -1;
            for (let idx = 0; idx < markers.length; idx += 1) {{
                const relation = markers[idx].compareDocumentPosition(input);
                if (relation & window.parent.Node.DOCUMENT_POSITION_FOLLOWING) {{
                    current = idx;
                }} else {{
                    break;
                }}
            }}
            return current;
        }}

        function updateNav() {{
            const markers = anchors();
            const answered = Array(questionCount).fill(false);
            const inputs = doc.querySelectorAll('input[type="radio"], input[type="checkbox"]');

            inputs.forEach((input) => {{
                if (!input.checked) return;
                const idx = questionForInput(input, markers);
                if (idx >= 0 && idx < questionCount) {{
                    answered[idx] = true;
                }}
            }});

            doc.querySelectorAll('.question-nav-item[data-question-index]').forEach((item) => {{
                const idx = Number(item.dataset.questionIndex);
                item.classList.toggle('answered', Boolean(answered[idx]));
            }});
            
            // The sticky behavior is now handled separately by sync_question_nav_sticky
        }}

        function inputFromEvent(event) {{
            const target = event.target;
            if (!target || !target.closest) return null;

            const directInput = target.closest('input[type="radio"], input[type="checkbox"]');
            if (directInput) return directInput;

            const label = target.closest('label');
            if (!label) return null;

            return label.querySelector('input[type="radio"], input[type="checkbox"]');
        }}

        function markAnswered(input) {{
            const idx = questionForInput(input, anchors());
            if (idx < 0 || idx >= questionCount) return;

            const item = doc.querySelector(`.question-nav-item[data-question-index="${{idx}}"]`);
            if (item) {{
                item.classList.add('answered');
            }}
        }}

        function handleEarlyInput(event) {{
            const input = inputFromEvent(event);
            if (!input) return;

            markAnswered(input);
            window.parent.requestAnimationFrame(updateNav);
            window.setTimeout(updateNav, 0);
            window.setTimeout(updateNav, 60);
        }}

        function refresh() {{
            updateNav();
        }}

        doc.addEventListener('pointerdown', handleEarlyInput, true);
        doc.addEventListener('mousedown', handleEarlyInput, true);
        doc.addEventListener('touchstart', handleEarlyInput, true);
        doc.addEventListener('click', handleEarlyInput, true);
        doc.addEventListener('change', () => window.setTimeout(updateNav, 0), true);
        refresh();
        const observer = new MutationObserver(refresh);
        observer.observe(doc.body, {{ childList: true, subtree: true }});
        window.setTimeout(refresh, 100);
        window.setTimeout(refresh, 500);
        window.setTimeout(refresh, 1200);
        window.setTimeout(refresh, 2500);
        </script>
        """,
        height=0,
    )


# ----------------- STAGE RENDERING FUNCTIONS -----------------
def render_upload_stage():
    st.markdown("### Bước 1. Nhập JSON đề thi")

    example_json = """
[
  {
    "id": ID của câu hỏi (số nguyên dương lớn hơn 0),
    "question": "Câu hỏi?",
    "type": "single" hoặc "multiple",
    "options": [
    "Đáp án A", "Đáp án B", "Đáp án C", "Đáp án D", "Đáp án E", ... (danh sách các đáp án, không nhất định phải là 5, nên tuỳ câu hỏi mà quyết định nên có bao nhiêu đáp án)
    ],
    "explanations": ["Đúng, vì...", "Sai, vì..."],
    "correct_answers": [danh sách INDEX  BẮT ĐẦU TỪ 0 của các đáp án đúng, chỉ một nếu type=="single", nhiều nếu type=="multiple"] 
  }
]
""".strip()

    json_text = st.text_area(
        "Danh sách câu hỏi (JSON). Mỗi phần tử là một object gồm các trường: "
        "`id`, `question`, `type` ('single' hoặc 'multiple'), `options` (list các đáp án), "
        "`correct_answers` (list index đáp án đúng, bắt đầu từ 0).",
        value=example_json,
        height=300,
    )

    uploaded_file = st.file_uploader(
        "Hoặc upload file đề thi (.json hoặc .txt)",
        type=["json", "txt"],
        help="File cần chứa nội dung JSON giống ô nhập bên trên.",
    )

    shuffle_questions = st.checkbox("Xáo trộn thứ tự câu hỏi", value=False)

    col_load, col_info = st.columns([1, 3])
    with col_load:
        load_btn = st.button("Tải đề thi / Cập nhật")

    with col_info:
        st.caption("Bạn có thể paste JSON hoặc upload file `.json` / `.txt`, rồi bấm **Tải đề thi** để cập nhật.")

    if load_btn:
        try:
            if uploaded_file is not None:
                source_text = uploaded_file.getvalue().decode("utf-8-sig")
            else:
                source_text = json_text

            load_questions_from_text(source_text)
            
            # Log upload event
            try:
                ip = get_client_ip()
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                num_q = len(st.session_state["questions"]) if st.session_state.get("questions") else 0
                conn = sqlite3.connect("visits.db")
                c = conn.cursor()
                c.execute("INSERT INTO uploads (ip_address, num_questions, uploaded_at) VALUES (?, ?, ?)", (ip, num_q, now_str))
                conn.commit()
                conn.close()
            except Exception:
                pass
            
            if shuffle_questions and st.session_state["questions"]:
                random.shuffle(st.session_state["questions"])
                
            st.session_state["current_stage"] = "exam"
            st.session_state["scroll_to_top"] = True
            st.rerun()
        except Exception as e:
            st.session_state["questions"] = None
            st.error(f"Lỗi khi đọc đề thi: {e}")


def render_exam_stage():
    questions = st.session_state.get("questions")
    if not questions:
        st.error("Không tìm thấy dữ liệu đề thi!")
        if st.button("Quay lại"):
            st.session_state["current_stage"] = "upload"
            st.session_state["scroll_to_top"] = True
            st.rerun()
        return

    st.markdown("### Bước 2. Làm bài thi")

    # layout chia 2 cột giống hình: trái là danh sách số câu, phải là nội dung
    col_nav, col_exam = st.columns([1, 3])

    with col_nav:
        if st.button("⬅ Quay lại", use_container_width=True):
            st.session_state["current_stage"] = "upload"
            st.session_state["scroll_to_top"] = True
            st.rerun()

        col_title, col_btn = st.columns([1, 1])
        with col_title:
            st.markdown("<h3 style='margin:0; padding:0;'>Câu hỏi</h3>", unsafe_allow_html=True)
        with col_btn:
            submit_btn = st.button("Nộp bài thi", type="primary", use_container_width=True)

        render_question_nav(questions)
        sync_question_nav_answer_state(len(questions))
        sync_question_nav_sticky()

        if submit_btn:
            total_score, detail_scores = grade_exam(questions)
            max_score = len(questions)
            
            # Log exam result
            try:
                ip = get_client_ip()
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                pct = (total_score / max_score) * 100 if max_score > 0 else 0
                conn = sqlite3.connect("visits.db")
                c = conn.cursor()
                c.execute("INSERT INTO exam_results (ip_address, total_score, max_score, percentage, submitted_at) VALUES (?, ?, ?, ?, ?)", (ip, total_score, max_score, pct, now_str))
                conn.commit()
                conn.close()
            except Exception:
                pass

            st.session_state["last_result"] = {
                "total": total_score,
                "detail": detail_scores,
                "max_score": max_score,
            }
            st.session_state["current_stage"] = "result"
            st.session_state["scroll_to_top"] = True
            st.rerun()

    with col_exam:
        st.subheader("Exam Questions")

        # hiển thị từng câu
        for i, q in enumerate(questions):
            st.markdown(
                f'<div id="question-{i + 1}" class="question-anchor"></div>',
                unsafe_allow_html=True,
            )
            st.markdown(f"**Question {i + 1}.** {q['question']}")
            q_type = q.get("type", "single")
            options = q["options"]

            if q_type == "single":
                st.radio(
                    "Chọn **một** đáp án:",
                    options,
                    key=f"q_{i}",
                    index=None,
                )
            else:
                st.write("Chọn **nhiều** đáp án (checkbox):")
                for j, opt in enumerate(options):
                    st.checkbox(opt, key=f"q_{i}_opt_{j}")
            st.markdown("---")


def render_result_stage():
    if "last_result" not in st.session_state:
        st.error("Chưa có kết quả thi!")
        if st.button("Quay lại"):
            st.session_state["current_stage"] = "upload"
            st.session_state["scroll_to_top"] = True
            st.rerun()
        return

    res = st.session_state["last_result"]
    questions = st.session_state.get("questions", [])

    pct = (res['total'] / res['max_score']) * 100 if res['max_score'] > 0 else 0
    if pct >= 90:
        title_msg = "Hehee giỏi waaa trời"
    elif pct >= 80:
        title_msg = "Cũng cũng=))))"
    else:
        title_msg = "Học lại nhanhhh"

    st.markdown(f"## Kết quả: {title_msg}")
    st.write(
        f"Điểm tổng: **{res['total']:.2f} / {res['max_score']}** "
        f"({pct:.1f}%)"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Làm lại bài này"):
            clear_answers()
            st.session_state["current_stage"] = "exam"
            st.session_state["scroll_to_top"] = True
            st.rerun()
    with col2:
        if st.button("Tải đề thi mới"):
            st.session_state["questions"] = None
            clear_answers()
            st.session_state["current_stage"] = "upload"
            st.session_state["scroll_to_top"] = True
            st.rerun()
            
    st.markdown("---")
    st.markdown("### Chi tiết từng câu (kèm đề và đáp án)")

    col_nav, col_result = st.columns([1, 3])
    
    with col_nav:
        st.markdown("<h3 style='margin:0; padding:0;'>Câu hỏi</h3>", unsafe_allow_html=True)
        render_result_question_nav(questions, res["detail"])
        sync_question_nav_sticky()

    with col_result:
        for i, d in enumerate(res["detail"]):
            st.markdown(
                f'<div id="question-{i + 1}" class="question-anchor"></div>',
                unsafe_allow_html=True,
            )
            st.markdown(f"**Question {i + 1}.** {d['question']} (Điểm: **{d['score']:.2f}**)")

            # hiển thị từng đáp án với icon trực quan
            for idx, opt in enumerate(d["options"]):
                is_correct = idx in d["correct_indices"]
                is_chosen = idx in d["user_indices"]

                if is_correct and is_chosen:
                    prefix = "✅"  # đúng và bạn chọn
                    note = " **(bạn chọn, đáp án đúng)**"
                elif is_correct and not is_chosen:
                    prefix = "☑️"  # đúng nhưng không chọn
                    note = " **(đáp án đúng, bạn bỏ sót)**"
                elif (not is_correct) and is_chosen:
                    prefix = "❌"  # sai nhưng bạn chọn
                    note = " **(bạn chọn sai)**"
                else:
                    prefix = "▫️"  # sai và không chọn
                    note = ""

                st.markdown(f"{prefix} {opt}{note}")

            # show explanations at the bottom of the question prominently
            explanations = d.get("explanations", [])
            valid_exps = [e for e in explanations if isinstance(e, str) and e.strip()]
            if valid_exps:
                st.info("\n\n".join(valid_exps), icon="💡")

            st.markdown("---")

# --- DB INIT ---
def init_db():
    conn = sqlite3.connect("visits.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT,
            visited_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT,
            num_questions INTEGER,
            uploaded_at DATETIME
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS exam_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT,
            total_score REAL,
            max_score REAL,
            percentage REAL,
            submitted_at DATETIME
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_client_ip():
    try:
        if hasattr(st, "context") and hasattr(st.context, "headers"):
            headers = st.context.headers
            ip = headers.get("X-Forwarded-For", headers.get("X-Real-IP", "Unknown IP"))
            if ip and ip != "Unknown IP":
                return ip.split(",")[0].strip()
    except Exception:
        pass
        
    try:
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        headers = _get_websocket_headers()
        ip = headers.get("X-Forwarded-For", "Unknown IP")
        if ip and ip != "Unknown IP":
            return ip.split(",")[0].strip()
    except Exception:
        pass
        
    return "Unknown IP"

def get_and_increment_visit_count():
    if "has_visited" not in st.session_state:
        st.session_state["has_visited"] = True
        ip = get_client_ip()
        
        # Lấy giờ thực tế của máy chủ thay vì để DB tự tạo (DB hay bị lệch múi giờ UTC)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            conn = sqlite3.connect("visits.db")
            c = conn.cursor()
            c.execute("INSERT INTO visits (ip_address, visited_at) VALUES (?, ?)", (ip, now_str))
            conn.commit()
            conn.close()
        except Exception:
            pass

    try:
        conn = sqlite3.connect("visits.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM visits")
        count = c.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0

def render_admin_stage():
    st.markdown("## Admin Dashboard - Thống kê Hoạt động")
    
    if st.button("Đăng xuất"):
        st.session_state.clear()
        st.rerun()
        
    try:
        conn = sqlite3.connect("visits.db")
        c = conn.cursor()
        
        # Lượt truy cập
        c.execute("SELECT id, ip_address, visited_at FROM visits ORDER BY visited_at DESC")
        visits_rows = c.fetchall()
        
        # Đề đã tải lên
        c.execute("SELECT id, ip_address, num_questions, uploaded_at FROM uploads ORDER BY uploaded_at DESC")
        uploads_rows = c.fetchall()
        
        # Kết quả thi
        c.execute("SELECT id, ip_address, total_score, max_score, percentage, submitted_at FROM exam_results ORDER BY submitted_at DESC")
        exam_rows = c.fetchall()
        
        conn.close()
        
        # Summary Metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Lượt truy cập", f"{len(visits_rows)}")
        with col2:
            st.metric("Số đề tải lên", f"{len(uploads_rows)}")
        with col3:
            st.metric("Số lượt thi", f"{len(exam_rows)}")
            
        st.markdown("---")
        
        # Tabs for details
        tab1, tab2, tab3 = st.tabs(["Lượt truy cập", "Lịch sử tải đề", "Kết quả thi"])
        
        with tab1:
            st.markdown("### Chi tiết lượt truy cập")
            if visits_rows:
                data = [{"ID": r[0], "IP Address": r[1], "Thời gian": r[2]} for r in visits_rows]
                st.dataframe(data, use_container_width=True)
            else:
                st.info("Chưa có dữ liệu.")
                
        with tab2:
            st.markdown("### Chi tiết tải đề")
            if uploads_rows:
                data = [{"ID": r[0], "IP Address": r[1], "Số câu hỏi": r[2], "Thời gian tải": r[3]} for r in uploads_rows]
                st.dataframe(data, use_container_width=True)
            else:
                st.info("Chưa có dữ liệu.")
                
        with tab3:
            st.markdown("### Lịch sử làm bài")
            if exam_rows:
                data = [{"ID": r[0], "IP Address": r[1], "Điểm": f"{r[2]:.2f} / {r[3]}", "Tỷ lệ (%)": f"{r[4]:.1f}%", "Thời gian nộp": r[5]} for r in exam_rows]
                st.dataframe(data, use_container_width=True)
            else:
                st.info("Chưa có dữ liệu.")
                
    except Exception as e:
        st.error(f"Lỗi truy xuất dữ liệu: {e}")

# ----------------- MAIN FLOW -----------------
require_password()

if st.session_state.get("is_admin"):
    render_admin_stage()
    st.stop()

st.title("A TTQT nhíeeeee")

# Gọi hàm để hệ thống ghi nhận lượt truy cập vào database, nhưng không hiển thị ra Sidebar
get_and_increment_visit_count()

if "questions" not in st.session_state:
    st.session_state["questions"] = None

if "current_stage" not in st.session_state:
    st.session_state["current_stage"] = "upload"

if st.session_state.get("scroll_to_top"):
    components.html(
        """
        <script>
            setTimeout(() => {
                const doc = window.parent.document;
                const containers = [
                    doc.querySelector('.main'),
                    doc.querySelector('[data-testid="stAppViewContainer"]'),
                    doc.querySelector('[data-testid="stMainBlockContainer"]'),
                    doc.documentElement,
                    doc.body,
                    window.parent
                ];
                containers.forEach(c => {
                    if (c && c.scrollTo) {
                        c.scrollTo({top: 0, behavior: 'instant'});
                    }
                });
            }, 50);
            
            setTimeout(() => {
                const doc = window.parent.document;
                const containers = [
                    doc.querySelector('.main'),
                    doc.querySelector('[data-testid="stAppViewContainer"]'),
                    doc.querySelector('[data-testid="stMainBlockContainer"]'),
                    doc.documentElement,
                    doc.body,
                    window.parent
                ];
                containers.forEach(c => {
                    if (c && c.scrollTo) {
                        c.scrollTo({top: 0, behavior: 'instant'});
                    }
                });
            }, 500);
        </script>
        """,
        height=0,
    )
    st.session_state["scroll_to_top"] = False

stage = st.session_state["current_stage"]

if stage == "upload":
    render_upload_stage()
elif stage == "exam":
    render_exam_stage()
elif stage == "result":
    render_result_stage()
