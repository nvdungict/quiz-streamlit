import json
import html

import streamlit as st

st.set_page_config(page_title="Quiz Demo", layout="wide")

st.markdown(
    """
    <style>
    html {
        scroll-behavior: smooth;
    }

    .question-nav {
        position: sticky;
        top: 1rem;
        max-height: calc(100vh - 2rem);
        overflow-y: auto;
        padding-right: 0.35rem;
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

    .question-anchor {
        scroll-margin-top: 1rem;
    }

    @media (max-width: 900px) {
        .question-nav {
            position: sticky;
            top: 0;
            z-index: 10;
            max-height: 42vh;
            padding: 0.75rem 0;
            background: rgb(14, 17, 23);
        }

        .question-nav-grid {
            grid-template-columns: repeat(6, minmax(2.5rem, 1fr));
            gap: 0.5rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


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
            f'href="#question-{idx + 1}" title="Question {idx + 1}">{label}</a>'
        )

    st.markdown(
        f"""
        <div class="question-nav">
            <div class="question-nav-title">Câu hỏi</div>
            <div class="question-nav-grid">
                {''.join(nav_items)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----------------- GIAO DIỆN NHẬP JSON -----------------
st.title("Exam Questions - Streamlit Demo")

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

col_load, col_info = st.columns([1, 3])
with col_load:
    load_btn = st.button("Tải đề thi / Cập nhật")

with col_info:
    st.caption("Bạn có thể paste JSON hoặc upload file `.json` / `.txt`, rồi bấm **Tải đề thi** để cập nhật.")

if "questions" not in st.session_state:
    st.session_state["questions"] = None

if load_btn:
    try:
        if uploaded_file is not None:
            source_text = uploaded_file.getvalue().decode("utf-8-sig")
        else:
            source_text = json_text

        load_questions_from_text(source_text)
        st.success("Đã tải đề thi thành công!")
    except Exception as e:
        st.session_state["questions"] = None
        st.error(f"Lỗi khi đọc đề thi: {e}")


# ----------------- GIAO DIỆN LÀM BÀI -----------------
questions = st.session_state.get("questions")

if questions:
    st.markdown("---")
    st.markdown("### Bước 2. Làm bài thi")

    # layout chia 2 cột giống hình: trái là danh sách số câu, phải là nội dung
    col_nav, col_exam = st.columns([1, 3])

    with col_nav:
        render_question_nav(questions)

    with col_exam:
        st.subheader("Exam Questions")

        # hiển thị từng câu
        for i, q in enumerate(questions):
            st.markdown(
                f'<div id="question-{i + 1}" class="question-anchor"></div>',
                unsafe_allow_html=True,
            )
            st.markdown(f"**Question {q.get('id', i+1)}.** {q['question']}")
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

        submit_btn = st.button("Nộp bài thi")

        if submit_btn:
            total_score, detail_scores = grade_exam(questions)
            st.session_state["last_result"] = {
                "total": total_score,
                "detail": detail_scores,
                "max_score": len(questions),  # mỗi câu tối đa 1 điểm
            }

        # luôn hiển thị kết quả gần nhất nếu có
        if "last_result" in st.session_state:
            res = st.session_state["last_result"]
            st.markdown("## Kết quả")
            st.write(
                f"Điểm tổng: **{res['total']:.2f} / {res['max_score']}** "
                f"({res['total'] / res['max_score'] * 100:.1f}%)"
            )

            st.markdown("### Chi tiết từng câu (kèm đề và đáp án)")
            for d in res["detail"]:
                st.markdown(f"#### Câu {d['id']} – điểm: **{d['score']:.2f}**")
                st.markdown(d["question"])

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
                    # show explanation for this option if provided in question data
                    explanations = d.get("explanations", [])
                    if idx < len(explanations) and explanations[idx]:
                        st.caption(explanations[idx])

                st.markdown("---")
else:
    st.info("Hãy nhập JSON đề thi và bấm **Tải đề thi / Cập nhật** để bắt đầu làm bài.")
