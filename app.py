import json

import streamlit as st

st.set_page_config(page_title="Quiz Demo", layout="wide")


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

col_load, col_info = st.columns([1, 3])
with col_load:
    load_btn = st.button("Tải đề thi / Cập nhật")

with col_info:
    st.caption("✅ Bạn có thể sửa JSON ở bên trên rồi bấm **Tải đề thi** để cập nhật.")

if "questions" not in st.session_state:
    st.session_state["questions"] = None

if load_btn:
    try:
        questions = json.loads(json_text)
        assert isinstance(questions, list), "JSON phải là một list các câu hỏi."
        # kiểm tra sơ bộ cấu trúc
        for q in questions:
            for field in ["question", "options", "correct_answers"]:
                assert field in q, f"Thiếu trường '{field}' trong một câu hỏi."
        st.session_state["questions"] = questions
        clear_answers()
        st.success("Đã tải đề thi thành công!")
    except Exception as e:
        st.session_state["questions"] = None
        st.error(f"Lỗi khi đọc JSON: {e}")


# ----------------- GIAO DIỆN LÀM BÀI -----------------
questions = st.session_state.get("questions")

if questions:
    st.markdown("---")
    st.markdown("### Bước 2. Làm bài thi")

    # layout chia 2 cột giống hình: trái là danh sách số câu, phải là nội dung
    col_nav, col_exam = st.columns([1, 3])

    with col_nav:
        st.markdown("#### Câu hỏi")
        n = len(questions)
        cols = st.columns(5)
        for idx in range(n):
            col = cols[idx % 5]
            with col:
                st.button(f"{idx+1}", key=f"nav_{idx}", help=f"Question {idx+1}")

    with col_exam:
        st.subheader("Exam Questions")

        # hiển thị từng câu
        for i, q in enumerate(questions):
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