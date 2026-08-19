"""Demo script for HybridMemoryAgent (Bonus Challenge Day 19).

Executes 5 illustrative queries demonstrating episodic memory + profile features.
"""
import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bonus.agent import HybridMemoryAgent


def main():
    print("================================================================")
    print("  INITIALIZING HYBRID MEMORY AGENT FOR USER: u_001")
    print("================================================================")
    agent = HybridMemoryAgent(user_id="u_001")

    # Seed some episodic memories for user u_001
    agent.remember("Hôm qua tôi vừa đọc tài liệu hướng dẫn cấu hình Kubernetes Cluster trên AWS EKS.", topic="cloud")
    agent.remember("Tôi đang tìm hiểu cách tối ưu bảo mật Cloud và quản lý IAM role cho container.", topic="security")
    agent.remember("Đã triển khai hệ thống tự động mở rộng (Auto-scaling) hạ tầng theo tải lượng người dùng.", topic="cloud")
    agent.remember("Ghi chú: Cần hoàn thành báo cáo tài chính quý 3 trước thứ Sáu tuần này.", topic="finance")
    agent.remember("Đã thử nghiệm mô hình ngôn ngữ lớn LLM kết hợp RAG với Qdrant vector database.", topic="ai_ml")

    queries = [
        ("Query 1 [Direct Keyword/Vector]", "Tôi đã đọc gì về Kubernetes?"),
        ("Query 2 [Profile-Aware Recommendation]", "Recommend tài liệu đọc tiếp theo cho tôi"),
        ("Query 3 [Recent Activity / Velocity]", "Tôi đang quan tâm và hoạt động gì gần đây?"),
        ("Query 4 [Paraphrase Query]", "Tài liệu về tự động mở rộng hạ tầng máy chủ?"),
        ("Query 5 [Mixed Hybrid + Profile]", "Cho tôi tóm tắt về cloud security và phân quyền"),
    ]

    for title, q in queries:
        print("\n----------------------------------------------------------------")
        print(f"🔹 {title}")
        print(f"❓ Prompt: '{q}'")
        print("----------------------------------------------------------------")
        context = agent.recall(q, user_id="u_001", top_k=2)
        print(context)

    print("\n================================================================")
    print("  DEMO EXITED SUCCESSFULLY (Exit 0)")
    print("================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
