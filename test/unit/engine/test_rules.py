"""Tests for :mod:`textmate_grammar.engine.rules` — port of the Rule classes,
``RuleRegistry`` and ``RuleFactory`` from vscode-textmate's ``rule.ts`` (v9.3.2).

vscode-textmate has no dedicated rule.ts unit test file upstream; this suite is
hand-written against rule.ts semantics, constructing rules from raw grammar dicts
the way upstream ``Grammar`` does (via ``initGrammar`` + ``RuleFactory``), and the
comments keep behavior pinned to the reference implementation's lines.
"""

from __future__ import annotations

from textmate_grammar.engine.oniglib import DEFAULT_ONIG_LIB, IOnigCaptureIndex
from textmate_grammar.engine.regexsource import RegExpSourceList
from textmate_grammar.engine.rules import (
    END_RULE_ID,
    WHILE_RULE_ID,
    BeginEndRule,
    BeginWhileRule,
    CaptureRule,
    IncludeOnlyRule,
    IncludeReferenceKind,
    MatchRule,
    Rule,
    RuleFactory,
    RuleRegistry,
    create_rule,
    init_grammar,
    parse_include,
)


def captures(*spans: tuple[int, int]) -> list[IOnigCaptureIndex]:
    return [IOnigCaptureIndex(start, end, end - start) for start, end in spans]


def registry() -> RuleRegistry:
    """A fresh registry backed by the default oniguruma adapter."""
    return RuleRegistry(DEFAULT_ONIG_LIB)


def self_repository(repository: dict) -> dict:
    """Wrap a repository dict as ``initGrammar`` would (grammar.ts:410-421)."""
    grammar = init_grammar({"scopeName": "source.test", "repository": repository})
    return grammar["repository"]


class TestIncludeReferenceParsing:
    def test_reference_kinds(self) -> None:
        # grammarDependencies.ts:278-295
        assert parse_include("$base").kind == IncludeReferenceKind.Base
        assert parse_include("$self").kind == IncludeReferenceKind.Self
        assert parse_include("#foo").kind == IncludeReferenceKind.RelativeReference
        assert parse_include("#foo").ruleName == "foo"
        assert parse_include("source.python").kind == IncludeReferenceKind.TopLevelReference
        external = parse_include("source.python#keyword")
        assert external.kind == IncludeReferenceKind.TopLevelRepositoryReference
        assert external.scopeName == "source.python"
        assert external.ruleName == "keyword"


class TestRuleRegistry:
    def test_ids_start_at_one_and_lookup_roundtrips(self) -> None:
        # grammar.ts:245-254 — ids increment from 1; getRule undoes registerRule
        reg = registry()
        one = reg.register_rule(lambda id: Rule(None, id, None, None))
        two = reg.register_rule(lambda id: Rule(None, id, None, None))
        assert (one.id, two.id) == (1, 2)
        assert reg.get_rule(1) is one
        assert reg.get_rule(2) is two

    def test_special_negative_ids(self) -> None:
        # rule.ts:17-20
        assert END_RULE_ID == -1
        assert WHILE_RULE_ID == -2

    def test_no_scope_name_interning_in_v9(self) -> None:
        # Deviation note: v9.3.2 records no scope-name -> ruleId map; ids are
        # purely numeric
        assert not hasattr(registry(), "_scope_name_2_rule_id")


class TestMatchRule:
    def test_created_from_raw_dict(self) -> None:
        reg = registry()
        repository = self_repository({})
        desc = {
            "name": "meta.class",
            "match": r"\b(class)\b",
            "captures": {"1": {"name": "keyword.control.class"}},
        }
        rule_id = create_rule(desc, reg, repository)
        assert rule_id == 1

        rule = reg.get_rule(rule_id)
        assert isinstance(rule, MatchRule)
        # rule.ts:129 — the match pattern carries this rule's id
        assert rule._match.rule_id == rule_id
        assert rule._match.source == r"\b(class)\b"

        # rule.ts:449-485 — the capture map becomes an indexed CaptureRule list
        # (index 0 is unused, so "1" yields a 2-item list)
        assert len(rule.captures) == 2
        assert isinstance(rule.captures[1], CaptureRule)
        assert rule.captures[1].getName("x", None) == "keyword.control.class"

    def test_captures_sparse_map(self) -> None:
        # rule.ts:466-468 — holes stay None, max id sizes the list
        reg = registry()
        repository = self_repository({})
        desc = {
            "match": "a(b)c(d)",
            "captures": {"4": {"name": "constant.other"}, "2": {"name": "keyword"}},
        }
        rule_id = create_rule(desc, reg, repository)
        rule = reg.get_rule(rule_id)
        assert isinstance(rule, MatchRule)
        assert len(rule.captures) == 5  # indices 0..4
        for missing in (0, 1, 3):
            assert rule.captures[missing] is None
        assert rule.captures[2].getName("x", None) == "keyword"
        assert rule.captures[4].getName("x", None) == "constant.other"

    def test_compile_and_scanning(self) -> None:
        # rule.ts:149-155 via CompiledRule.findNextMatchSync
        reg = registry()
        repository = self_repository({})
        desc = {"match": "aa", "captures": {"1": {"name": "name"}}}
        rule_id = create_rule(desc, reg, repository)
        rule = reg.get_rule(rule_id)

        compiled = rule.compile(reg, None)
        match = compiled.find_next_match_sync("a aa", 0)
        assert match is not None
        assert match.rule_id == rule_id  # the match pattern carries the rule id

        compiled_ag = rule.compileAG(reg, None, allowA=False, allowG=False)
        match_ag = compiled_ag.find_next_match_sync("a aa", 0)
        assert match_ag is not None
        assert match_ag.rule_id == rule_id


class TestBeginEndRule:
    def matlab_grammar(self) -> dict:
        """A matlab-style begin/end block rule: the vendored upstream shape."""
        return {
            "scopeName": "source.matlab.test",
            "repository": {
                "function-block": {
                    "begin": r"(?i)\\b(function)\\b",
                    "beginCaptures": {
                        "1": {"name": "storage.type.function.matlab"},
                    },
                    "end": r"^\s*$",  # rule.ts:224-225 — the end rule id is -1
                    "endCaptures": {"0": {"name": "meta.function.end"}},
                    "patterns": [
                        {"include": "#parameters"},
                        {"match": "functionbody", "captures": {"0": {"name": "meta"}}},
                    ],
                },
                "parameters": {
                    "name": "meta.parameters",
                    "match": r"\(.*?\)",
                    "captures": {"0": {"name": "punctuation.parenthesis.matlab"}},
                },
            },
        }

    def test_begin_end_created_from_raw_dict(self) -> None:
        reg = registry()
        repository = self_repository(self.matlab_grammar()["repository"])
        desc = repository["function-block"]

        rule_id = create_rule(desc, reg, repository)
        rule = reg.get_rule(rule_id)
        assert isinstance(rule, BeginEndRule)

        # rule.ts:222/224 — begin carries the rule id, end carries endRuleId (-1)
        assert rule._begin.rule_id == rule_id
        assert rule._end.rule_id == END_RULE_ID
        assert rule.applyEndPatternLast is False
        assert rule.endHasBackReferences is False

        # rule.ts:438-441 — beginCaptures wins over rule-level captures
        assert isinstance(rule.beginCaptures[1], CaptureRule)
        assert (
            rule.beginCaptures[1].getName("x", None) == "storage.type.function.matlab"
        )
        assert isinstance(rule.endCaptures[0], CaptureRule)

        # ids: block=1, begin-capture=2, end-capture=3, parameters=4,
        # body-capture=5, body match=6 (captures compile before the patterns,
        # rule.ts:433-442)
        assert rule.patterns == (4, 6)

    def test_pattern_id_order_is_declaration_order(self) -> None:
        reg = registry()
        repository = self_repository(
            {
                "first": {"match": "one"},
                "second": {"match": "two"},
                "block": {"begin": "b", "end": "e", "patterns": [{"include": "#first"}, {"include": "#second"}]},
            }
        )
        rule_id = create_rule(repository["block"], reg, repository)
        rule = reg.get_rule(rule_id)
        assert isinstance(rule, BeginEndRule)
        # the block is registered first (its factory compiles the patterns
        # inline, rule.ts:391-392), so ids stay declaration-ordered among the
        # *patterns* (first=2, second=3) while the block itself is id 1
        assert repository["first"]["id"] == 2
        assert repository["second"]["id"] == 3
        assert rule.id == 1
        assert rule.patterns == (2, 3)

    def test_compile_ag_contains_end_source(self) -> None:
        reg = registry()
        repository = self_repository(
            {"block": {"begin": "b", "end": "e", "patterns": [{"match": "m"}]}}
        )
        rule_id = create_rule(repository["block"], reg, repository)
        rule = reg.get_rule(rule_id)

        # rule.ts:273-277 — the end source sits first (applyEndPatternLast=False)
        compiled = rule.compileAG(reg, "", allowA=False, allowG=False)
        assert compiled.find_next_match_sync("e", 0) is not None
        assert compiled.find_next_match_sync("e", 0).rule_id == END_RULE_ID

    def test_apply_end_pattern_last(self) -> None:
        # rule.ts:227, 273-277 — the end source moves to the last position
        reg = registry()
        repository = self_repository(
            {
                "block": {
                    "begin": "b",
                    "end": "e",
                    "applyEndPatternLast": True,
                    "patterns": [{"match": "m"}],
                }
            }
        )
        rule_id = create_rule(repository["block"], reg, repository)
        rule = reg.get_rule(rule_id)
        assert rule.applyEndPatternLast is True
        # end follows the inner pattern: scan sources via the compiled scanner
        compiled = rule.compileAG(reg, "", allowA=False, allowG=False)
        hit_at_one = compiled.find_next_match_sync("e", 0)
        assert hit_at_one is not None
        assert hit_at_one.rule_id == END_RULE_ID

    def test_end_back_references_resolved(self) -> None:
        # rule.ts:248-250, 279-285 — `$1`-style end refs substitute begin captures
        reg = registry()
        repository = self_repository(
            {
                "block": {
                    "begin": r"\A'(.*?)'",  # capture 1 = quoted content
                    "end": r"\1",
                    "beginCaptures": {"1": {"name": "quote.mark"}},
                    "patterns": [],
                }
            }
        )
        rule_id = create_rule(repository["block"], reg, repository)
        rule = reg.get_rule(rule_id)
        assert isinstance(rule, BeginEndRule)
        assert rule.endHasBackReferences is True

        # the raw end source still carries the backreference...
        assert rule._end.source == r"\1"
        # ...resolving against the begin match replaces it with escaped content.
        # Begin match "it's 'sunshine'": capture 1 = (5,15) = "'sunshine'" (both
        # quotes included — in real grammars the begin captures the text to echo)
        resolved = rule.getEndWithResolvedBackReferences(
            "it's 'sunshine'", captures((0, 4), (5, 15))
        )
        assert resolved == "'sunshine'"

    def test_end_back_reference_swapped_in_compilation(self) -> None:
        # rule.ts:279-285 — the compiled end source replaces the backreference
        reg = registry()
        repository = self_repository(
            {"block": {"begin": r"«(.*)»", "end": r"\1", "beginCaptures": {"1": {"name": "q"}}, "patterns": []}}
        )
        rule_id = create_rule(repository["block"], reg, repository)
        rule = reg.get_rule(rule_id)

        # No captures present: $1 substitutes ''
        end_source = rule.getEndWithResolvedBackReferences("no match", captures((0, 0)))
        assert end_source == ""
        assert rule.compileAG(reg, end_source, allowA=False, allowG=True) is not None


class TestBeginWhileRule:
    def while_grammar(self) -> dict:
        return {
            "repository": {
                "while-block": {
                    "begin": r"function\b",
                    "beginCaptures": {"1": {"name": "storage.type"}},
                    "while": r"^\s*;",
                    "whileCaptures": {"0": {"name": "meta.while"}},
                    "patterns": [{"match": "stmt"}],
                }
            }
        }

    def test_while_created_from_raw_dict(self) -> None:
        reg = registry()
        repository = self_repository(self.while_grammar()["repository"])
        desc = repository["while-block"]

        rule_id = create_rule(desc, reg, repository)
        rule = reg.get_rule(rule_id)
        assert isinstance(rule, BeginWhileRule)

        # rule.ts:306 — the while pattern carries whileRuleId (-2)
        assert rule._while.rule_id == WHILE_RULE_ID
        assert rule.whileHasBackReferences is False
        assert isinstance(rule.whileCaptures[0], CaptureRule)
        # rule.ts:349-359 — patterns compile without any end source
        assert len(rule.patterns) == 1

    def test_compile_while_yields_while_rule_id(self) -> None:
        # rule.ts:361-378
        reg = registry()
        repository = self_repository(self.while_grammar()["repository"])
        rule = reg.get_rule(create_rule(repository["while-block"], reg, repository))
        assert isinstance(rule, BeginWhileRule)

        compiled_while = rule.compileWhile(reg, None)
        while_match = compiled_while.find_next_match_sync("  ; y", 0)
        assert while_match is not None
        assert while_match.rule_id == WHILE_RULE_ID

        # this rule's *children* compile along the main path (the while rule never
        # compiles its own begin — rule.ts:349-359; the begin only surfaces when
        # the rule is included by a parent's collectPatterns, rule.ts:337-339)
        compiled = rule.compileAG(reg, None, allowA=False, allowG=True)
        child_match = compiled.find_next_match_sync("a stmt here", 0)
        assert child_match is not None
        assert child_match.rule_id == rule.patterns[0]

    def test_while_back_references(self) -> None:
        # rule.ts:333-335, 369-378
        reg = registry()
        repository = self_repository(
            {"block": {"begin": r"(«)(.*?)(»)", "while": r"\1", "patterns": []}}
        )
        rule_id = create_rule(repository["block"], reg, repository)
        rule = reg.get_rule(rule_id)
        assert isinstance(rule, BeginWhileRule)
        assert rule.whileHasBackReferences is True

        resolved = rule.getWhileWithResolvedBackReferences("«abc»", captures((0, 5), (0, 1)))
        assert resolved == "«"


class TestIncludeOnlyRule:
    def test_include_only_pattern(self) -> None:
        # rule.ts:409-411 — a bare include becomes the pattern list
        reg = registry()
        repository = self_repository(
            {
                "target": {"name": "target.rule", "match": "target"},
                "includer": {"include": "#target"},
            }
        )
        rule_id = create_rule(repository["includer"], reg, repository)
        rule = reg.get_rule(rule_id)
        assert isinstance(rule, IncludeOnlyRule)

        patterns: RegExpSourceList = RegExpSourceList()
        rule.collectPatterns(reg, patterns)
        assert len(patterns) == 1
        compiled = rule.compileAG(reg, None, allowA=False, allowG=False)
        match = compiled.find_next_match_sync("a target", 0)
        assert match is not None
        # the collected pattern is the referenced match rule's own pattern
        assert match.rule_id == reg.get_rule(repository["target"]["id"]).id

    def test_self_include(self) -> None:
        # rule.ts:502 — `$self` resolves through repository['$self']
        reg = registry()
        repository = self_repository(
            {
                "loop": {"match": "loop"},
                "wrapper": {"include": "$self", "name": "wrapper"},
            }
        )
        rule_id = create_rule(repository["wrapper"], reg, repository)
        rule = reg.get_rule(rule_id)
        assert isinstance(rule, IncludeOnlyRule)
        # $self resolves to the repository's $self entry, whose patterns are the
        # top-level ones — the loop match rule, compiled fresh at registration
        # time (wrapper itself is id 1, so the loop match gets id 2)
        assert rule.patterns == (2,)

    def test_base_include(self) -> None:
        # rule.ts:502 — `$base` resolves through repository['$base']
        reg = registry()
        # the base grammar's $self hook (as an embedding grammar would get it via
        # initGrammar(grammar, repository.$base), grammar.ts:267-270)
        # the base grammar — its *top-level patterns* (not the repository) are
        # what $self installs (grammar.ts:414-418)
        base = init_grammar(
            {
                "scopeName": "source.base",
                "patterns": [{"match": "rootrule"}],
                "repository": {"aux": {"match": "aux"}},
            }
        )

        # a grammar with a `$base`-explicit repository: init_grammar's second
        # argument installs the embedding grammar's $self as this grammar's $base
        nested = init_grammar(
            {"scopeName": "source.other", "repository": {"unique": {"include": "$base"}}},
            base["repository"]["$self"],
        )
        repository = nested["repository"]

        rule_id = create_rule(repository["unique"], reg, repository)
        rule = reg.get_rule(rule_id)
        assert isinstance(rule, IncludeOnlyRule)
        # $base of the nested repository is the outer grammar's $self entry; the
        # root match rule compiles into its own id (unique=1, root=2)
        assert rule.patterns == (2,)
        compiled = rule.compileAG(reg, None, allowA=False, allowG=False)
        match = compiled.find_next_match_sync("a rootrule", 0)
        assert match is not None
        # the chain is unique(1) → $base's $self IncludeOnlyRule(2) → its top
        # pattern MatchRule(3); collectPatterns flattens the whole chain
        assert match.rule_id == 3

    def test_missing_rule_include_dropped_and_flag_set(self) -> None:
        # rule.ts:507-513 — a repository include to a missing rule is dropped, and
        # _compilePatterns records hasMissingPatterns implicitly (no $ref check upstream)
        reg = registry()
        repository = self_repository(
            {"ghost": {"include": "#nowhere"}, "real": {"match": "real"}}
        )
        rule_id = create_rule(repository["ghost"], reg, repository)
        rule = reg.get_rule(rule_id)
        assert isinstance(rule, IncludeOnlyRule)
        assert len(rule.patterns) == 0
        assert rule.hasMissingPatterns is True


class TestRecursion:
    def test_recursive_repository(self) -> None:
        # a repository referencing itself terminates (desc.id memoization,
        # rule.ts:390-392)
        reg = registry()
        repository = self_repository(
            {
                "outer": {
                    "name": "outer.rule",
                    "patterns": [{"include": "#outer"}, {"match": "x"}],
                }
            }
        )
        rule_id = create_rule(repository["outer"], reg, repository)
        rule = reg.get_rule(rule_id)
        assert isinstance(rule, IncludeOnlyRule)
        assert rule.patterns == (rule_id, 2)

    def test_includer_skips_empty_pattern_skeleton(self) -> None:
        # rule.ts:550-562 — a referenced rule whose own pattern list dropped to
        # empty-with-missing gets removed entirely from the includer's list
        reg = registry()
        repository = self_repository(
            {
                "skeleton": {"include": "#missing-anchor", "name": "skeleton"},
                "includer": {"patterns": [{"include": "#skeleton"}, {"match": "keep"}]},
            }
        )
        rule_id = create_rule(repository["includer"], reg, repository)
        rule = reg.get_rule(rule_id)
        assert isinstance(rule, IncludeOnlyRule)
        # 'skeleton' dropped (hasMissingPatterns + no patterns; ids: includer=1,
        # skeleton=2, keep=3), so only 'keep' remains
        assert rule.patterns == (3,)


class TestNameCaptureExpansion:
    def test_name_expansion(self) -> None:
        # rule.ts:70-82 via RegexSource.replaceCaptures
        reg = registry()
        rule = MatchRule(
            None, 1, "scope.$1", "word", [CaptureRule(None, 2, "sub.scope", None, 0)]
        )
        assert rule.getName("a word b", captures((0, 0), (2, 6))) == "scope.word"
        assert rule.getContentName("a word b", captures((0, 0), (2, 6))) is None


class TestMisc:
    def test_debug_name(self) -> None:  # noqa: N803
        # rule.ts:65-68
        rule = Rule({"filename": "grammars/x.tmLanguage", "line": 7}, 3, "n", None)
        assert rule.debugName == "Rule#3 @ x.tmLanguage:7"
        assert MatchRule(None, 1, None, "a", []).debugName == "MatchRule#1 @ unknown"


class TestCompileAGAnchored:
    def test_anchored_begin_uses_compile_ag_variants(self) -> None:
        # rule.ts:260-262 — compileAG resolves anchors via the RegExpSourceList
        # anchor cache. Note: a rule's own begin is NOT in its compiled list
        # (rule.ts:264-277 collects only children + the end) — the begin surfaces
        # when the rule is *included* by a parent (rule.ts:252-254), so scan
        # through a wrapper include rule here.
        reg = registry()
        repository = self_repository(
            {
                "block": {"begin": r"\A``", "end": r"\Gx", "patterns": []},
                "wrapper": {"include": "#block", "name": "wrapper.rule"},
            }
        )
        wrapper_id = create_rule(repository["wrapper"], reg, repository)
        wrapper = reg.get_rule(wrapper_id)
        assert isinstance(wrapper, IncludeOnlyRule)
        block_id = wrapper.patterns[0]

        # A1_G1 keeps both anchors: the begin (\A`` at string start) matches
        compiled = wrapper.compileAG(reg, "", allowA=True, allowG=True)
        hit = compiled.find_next_match_sync("``x", 0)
        assert hit is not None
        assert hit.rule_id == block_id
        # from a later offset \A fails, nothing at all matches
        assert compiled.find_next_match_sync("``x", 2) is None

        # A0_G0 neutralizes both anchors to U+FFFF: the begin cannot match
        compiled_dead = wrapper.compileAG(reg, "", allowA=False, allowG=False)
        assert compiled_dead.find_next_match_sync("``x", 0) is None

    def test_no_missing_patterns_when_complete(self) -> None:
        # rule.ts:568-571 — a fully resolved list has the flag False
        reg = registry()
        repository = self_repository({"block": {"patterns": [{"match": "m"}]}})
        rule_id = create_rule(repository["block"], reg, repository)
        rule = reg.get_rule(rule_id)
        assert isinstance(rule, IncludeOnlyRule)
        assert rule.hasMissingPatterns is False
        assert len(rule.patterns) == 1
