from app.services.documents import PolicyPage, chunk_policy_pages


def test_chunks_policy_pages():
    pages = [
        PolicyPage(
            policy_name="Information Security Policy",
            category="Information Security",
            framework="NIST",
            page=1,
            text="POLICY\n" + ("Access controls must be documented. " * 220),
        )
    ]
    chunks = chunk_policy_pages(pages, chunk_size=500, overlap=50)
    assert len(chunks) > 1
    assert chunks[0].section == "Policy"
