"""Simple benchmark for 10 multi-turn conversations."""
import argparse
import io
import json
import os
import sys
import time
import unicodedata
import uuid
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent.graph import create_memory_agent
from src.llm import LLMClient
from src.utils.prompt_builder import build_prompt_with_memory
from src.utils.token_counter import estimate_tokens


def normalize_text(text: str) -> str:
    text = text.lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return " ".join(text.split())


def matches_groups(text: str, groups: list[list[str]]) -> bool:
    normalized = normalize_text(text)
    return all(
        any(normalize_text(option) in normalized for option in group)
        for group in groups
    )


def summarize(text: str, limit: int = 180) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


class NoMemoryAgent:
    def __init__(self):
        self.llm = LLMClient()

    def chat(self, user_message: str) -> str:
        return self.llm.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "Bạn là trợ lý không có bộ nhớ. "
                        "Chỉ dùng thông tin trong tin nhắn hiện tại. "
                        "Nếu thiếu dữ kiện thì nói rõ là bạn chưa biết."
                    ),
                },
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
        )


SCENARIOS = [
    {
        "name": "1. Profile Recall + IT Helpdesk",
        "conversation": [
            "Xin chào, tôi tên là Minh, làm IT Support.",
            "Tôi quên mật khẩu rồi.",
            "Bạn còn nhớ tên và công việc của tôi không? Và cách reset password?",
        ],
        "expected": [["minh"], ["it support"], ["sso.company.internal/reset", "ext. 9000"]],
        "profile_contains": "Minh",
    },
    {
        "name": "2. Conflict Update - Allergy",
        "conversation": [
            "Tôi dị ứng sữa bò.",
            "À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò.",
            "Tôi dị ứng gì?",
        ],
        "expected": [["đậu nành", "dau nanh"]],
        "profile_contains": "đậu nành",
    },
    {
        "name": "3. Episodic Recall - VPN Issue",
        "conversation": [
            "Tôi gặp lỗi VPN bị disconnect liên tục.",
            "Đã fix bằng cách kiểm tra Internet và restart VPN client.",
            "Lần sau gặp lỗi VPN thì làm gì?",
        ],
        "expected": [["internet"], ["restart vpn", "vpn client"]],
        "episode_contains": [["vpn"], ["internet"], ["restart"]],
    },
    {
        "name": "4. Semantic - Leave Policy",
        "conversation": [
            "Tôi có 4 năm kinh nghiệm, được bao nhiêu ngày phép năm?",
            "Nếu nghỉ ốm quá 3 ngày thì cần gì?",
            "Remote work được mấy ngày một tuần?",
        ],
        "expected": [["15 ngày", "15 ngay"], ["giấy", "giay"], ["2 ngày", "2 ngay"]],
    },
    {
        "name": "5. Semantic - SLA P1",
        "conversation": [
            "SLA cho ticket P1 là bao lâu?",
            "Nếu không có phản hồi trong 10 phút thì sao?",
            "Ticket P2 thì resolution time là bao lâu?",
        ],
        "expected": [["4 giờ", "4 gio"], ["senior engineer"], ["1 ngày", "1 ngay"]],
    },
    {
        "name": "6. Semantic - Refund Policy",
        "conversation": [
            "Khách hàng muốn hoàn tiền, điều kiện là gì?",
            "Nếu đơn hàng là license key thì có được hoàn không?",
            "Thời gian xử lý hoàn tiền mất bao lâu?",
        ],
        "expected": [["7 ngày", "7 ngay"], ["license key", "kỹ thuật số", "ky thuat so"], ["3-5 ngày", "3-5 ngay"]],
    },
    {
        "name": "7. Semantic - Access Control",
        "conversation": [
            "Nhân viên mới cần quyền truy cập Level 2, phải làm gì?",
            "Thời gian xử lý là bao lâu?",
            "Còn Level 4 Admin Access thì cần gì?",
        ],
        "expected": [["it-access"], ["2 ngày", "2 ngay"], ["ciso", "training"]],
    },
    {
        "name": "8. Multi-Memory - IT Admin Role",
        "conversation": [
            "Tôi tên là Hùng, làm IT Admin.",
            "Có nhân viên cần cấp quyền khẩn cấp trong sự cố P1.",
            "Theo quy trình, tôi có thể cấp quyền tạm thời không?",
        ],
        "expected": [["hùng", "hung"], ["it admin"], ["24 giờ", "24 gio", "24h"], ["tech lead"]],
        "profile_contains": "IT Admin",
    },
    {
        "name": "9. Episode Chain - Ticket Handling",
        "conversation": [
            "Tôi xử lý ticket P1 về database sập.",
            "Đã resolve trong 3 giờ bằng cách restart service.",
            "Giờ có ticket P2 về API lỗi, kinh nghiệm P1 có giúp gì không?",
        ],
        "expected": [["restart service", "restart"], ["check logs", "kiểm tra log", "kiem tra log"]],
        "episode_contains": [["database"], ["restart"]],
    },
    {
        "name": "10. Long Context - Token Budget",
        "conversation": [
            "Tôi tên là Lan.",
            "Tôi làm HR Manager.",
            "Tôi đang tổng hợp leave policy cho nhóm có trên 5 năm kinh nghiệm và cần nhắc team dùng HR Portal đúng quy trình.",
            "Ngoài ra tôi còn cần nhắc team rằng remote work chỉ áp dụng sau probation và onsite bắt buộc vào thứ 3, thứ 5.",
            "Bạn nhớ tên và vai trò của tôi không? Tóm tắt lại các policy quan trọng tôi vừa hỏi.",
        ],
        "expected": [["lan"], ["hr manager"], ["18 ngày", "18 ngay"], ["2 ngày", "2 ngay"], ["thứ 3", "thu 3"], ["thứ 5", "thu 5"]],
        "check_budget": True,
    },
]


def run_conversation(agent, conversation, label):
    responses = []
    for index, user_message in enumerate(conversation, start=1):
        print(f"\n[{label}] Turn {index}")
        print(f"User: {user_message}")
        response = agent.chat(user_message)
        print(f"Agent: {response}")
        responses.append(response)
    return responses


def extra_checks(memory_agent, scenario):
    details = []
    ok = True

    if scenario.get("profile_contains"):
        profile_text = json.dumps(memory_agent.profile.get_profile(), ensure_ascii=False)
        profile_ok = normalize_text(scenario["profile_contains"]) in normalize_text(profile_text)
        details.append(f"profile={profile_text}")
        ok = ok and profile_ok

    if scenario.get("episode_contains"):
        episode_text = json.dumps(memory_agent.episodic.get_episodes(limit=3), ensure_ascii=False)
        episode_ok = matches_groups(episode_text, scenario["episode_contains"])
        details.append(f"episodes={episode_text}")
        ok = ok and episode_ok

    if scenario.get("check_budget"):
        last_message = scenario["conversation"][-1]
        prompt = build_prompt_with_memory(
            user_message=last_message,
            user_profile=memory_agent.profile.get_profile(),
            episodes=memory_agent.episodic.search_episodes(last_message, limit=3),
            semantic_hits=memory_agent.semantic.search(last_message, top_k=3),
            recent_conversation=memory_agent.short_term.get_recent_text(num_messages=6),
            memory_budget=2000,
        )
        tokens = estimate_tokens(prompt[1]["content"])
        details.append(f"memory_tokens={tokens}")
        ok = ok and tokens <= 2000

    return ok, " | ".join(details)


def run_benchmark(output_path: Path | None = None):
    results = []

    print("=" * 72)
    print("BENCHMARK: Multi-Memory Agent")
    print("=" * 72)

    for index, scenario in enumerate(SCENARIOS, start=1):
        print("\n" + "=" * 72)
        print(f"Scenario {index}: {scenario['name']}")
        print("=" * 72)

        baseline = NoMemoryAgent()
        memory_agent = create_memory_agent(
            user_id=f"benchmark_user_{index}_{uuid.uuid4().hex[:8]}",
            use_redis=False,
        )

        no_memory_responses = run_conversation(baseline, scenario["conversation"], "no-memory")
        with_memory_responses = run_conversation(memory_agent, scenario["conversation"], "with-memory")

        joined_no_memory = "\n".join(no_memory_responses)
        joined_with_memory = "\n".join(with_memory_responses)

        main_pass = matches_groups(joined_with_memory, scenario["expected"])
        extra_pass, detail = extra_checks(memory_agent, scenario)
        passed = main_pass and extra_pass

        result = {
            "scenario": scenario["name"],
            "no_memory_summary": summarize(joined_no_memory),
            "with_memory_summary": summarize(joined_with_memory),
            "no_memory_responses": no_memory_responses,
            "with_memory_responses": with_memory_responses,
            "details": detail,
            "passed": passed,
        }
        results.append(result)

        print(f"\nResult: {'PASS' if passed else 'FAIL'}")
        if detail:
            print(f"Detail: {detail}")

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(
                {
                    "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "passed": sum(1 for item in results if item["passed"]),
                    "total": len(results),
                    "results": results,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)
    for index, result in enumerate(results, start=1):
        print(f"{index:>2}. {'PASS' if result['passed'] else 'FAIL'} - {result['scenario']}")

    passed = sum(1 for item in results if item["passed"])
    print(f"\nOverall: {passed}/{len(results)} scenarios passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    raise SystemExit(run_benchmark(args.output))
