"""Help content is complete, consistent, and searchable without Blender."""
from framemill import guide, help_content


def test_invariants_and_coverage():
    help_content.check_invariants()
    assert {c.id for c in help_content.CATEGORIES} == {a.category for a in help_content.ARTICLES}


def test_search_empty_and_keywords():
    assert help_content.search("") == []
    assert help_content.search("   ") == []
    pink = help_content.search("magic pink")
    assert pink and pink[0].id in {"exporting", "ref-export"}
    orbit = help_content.search("orbit distance")
    assert orbit and orbit[0].id in {"camera-framing", "ref-appearance"}
    master = help_content.search("master palette")
    assert master and master[0].id == "dos-master-palette"
    assert help_content.search("dos palette")
    assert help_content.search("index 0")
    assert help_content.search("remove root motion")
    assert help_content.search("custom colours")[0].id == "custom-fixed-colours"
    assert help_content.search("fixed colours")
    assert help_content.search("master palette file")[0].id == "create-master-palette"
    assert help_content.search("create palette")
    assert help_content.search("fit basis")
    assert help_content.article_by_id("custom-fixed-colours").category == "export"
    assert help_content.article_by_id("create-master-palette").category == "export"


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


def test_every_listed_control_is_searchable():
    missing = [key for key in help_content.CONTROL_KEYWORDS if not help_content.search(key)]
    assert missing == []
    assert help_content.articles_in("reference")


def test_workflow_pipeline_terms_are_searchable():
    missing = [key for key in help_content.WORKFLOW_KEYWORDS if not help_content.search(key)]
    assert missing == []
    assert help_content.article_by_id("rig-mixamo").category == "getting-started"
    assert help_content.article_by_id("make-a-model").category == "getting-started"
