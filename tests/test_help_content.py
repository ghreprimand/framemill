"""Help content is complete, consistent, and searchable without Blender."""
from framemill import guide, help_content


def test_invariants_and_coverage():
    help_content.check_invariants()
    assert {c.id for c in help_content.CATEGORIES} == {a.category for a in help_content.ARTICLES}


def test_search_empty_and_keywords():
    assert help_content.search("") == []
    assert help_content.search("   ") == []
    pink = help_content.search("magic pink")
    assert pink and pink[0].id == "exporting"
    orbit = help_content.search("orbit distance")
    assert orbit and orbit[0].id == "camera-framing"


def test_title_ranks_above_body_only():
    ranked = help_content.search("camera")
    assert ranked
    assert ranked[0].id == "camera-framing"
    assert any(article.id == "troubleshooting" for article in ranked)


def test_guide_wording_is_preserved():
    blob = " ".join(help_content.article_text(article) for article in help_content.ARTICLES)
    steps = (guide.SETUP_STEPS + guide.WORKFLOW_STEPS + guide.ANIMATION_STEPS
             + guide.TROUBLESHOOTING_STEPS)
    for step in steps:
        assert step.body in blob
        assert step.title in blob


def test_placeholders_and_lookups():
    assert help_content.REPO_URL == "https://github.com/ghreprimand/framemill"
    assert help_content.BRAND_URL == "https://unfinished-works.com"
    assert help_content.article_by_id("first-sheet").category == "getting-started"
    assert help_content.articles_in("about")[0].id == "about"
