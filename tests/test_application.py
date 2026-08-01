from scholarship_factory.application import (
    ApplicationRequirements,
    EssayPrompt,
    RequirementsStore,
    read_requirements,
)


class StubClient:
    def __init__(self, payload):
        self._payload = payload
        self.messages = self
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        block = type("Block", (), {"type": "tool_use", "input": self._payload})()
        return type("Message", (), {"content": [block]})()


def test_read_requirements_maps_prompts_and_documents():
    client = StubClient(
        {
            "is_application_page": True,
            "essay_prompts": [
                {"prompt": "Why do you deserve this award?", "word_limit": 500},
                {"prompt": "Describe a challenge you overcame."},
            ],
            "documents": ["Official transcript", "CV"],
            "referees": 2,
            "other_requirements": ["Proof of enrolment"],
        }
    )

    result = read_requirements("<html></html>", "https://e.com/apply", client=client)

    assert result.essay_prompts[0].word_limit == 500
    assert result.essay_prompts[1].word_limit is None  # not stated, not guessed
    assert result.documents == ["Official transcript", "CV"]
    assert result.referees == 2


def test_page_text_is_cleaned_before_the_call():
    client = StubClient({"is_application_page": True})
    read_requirements(
        "<html><body><p>Apply here</p><script>junk()</script></body></html>",
        "https://e.com/apply",
        client=client,
    )

    sent = client.last_kwargs["messages"][0]["content"]
    assert "Apply here" in sent
    assert "junk()" not in sent


def test_non_application_page_is_flagged_and_empty():
    client = StubClient({"is_application_page": False})
    result = read_requirements("<html></html>", "https://e.com/login", client=client)

    assert result.is_application_page is False
    assert result.essay_prompts == []
    assert result.referees is None


def test_requirements_store_round_trip_and_overwrite(tmp_path):
    store = RequirementsStore(str(tmp_path / "t.db"))
    store.set(
        "opp-1",
        ApplicationRequirements(essay_prompts=[EssayPrompt(prompt="First", word_limit=100)]),
    )
    assert store.get("opp-1").essay_prompts[0].prompt == "First"

    store.set("opp-1", ApplicationRequirements(referees=3))
    stored = store.get("opp-1")
    assert stored.referees == 3
    assert stored.essay_prompts == []
    assert len(store.all()) == 1


def test_missing_requirements_is_none(tmp_path):
    assert RequirementsStore(str(tmp_path / "t.db")).get("nope") is None
