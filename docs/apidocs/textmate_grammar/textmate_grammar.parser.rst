:py:mod:`textmate_grammar.parser`
=================================

.. py:module:: textmate_grammar.parser

.. autodoc2-docstring:: textmate_grammar.parser
   :allowtitles:

Module Contents
---------------

Classes
~~~~~~~

.. list-table::
   :class: autosummary longtable
   :align: left

   * - :py:obj:`GrammarParser <textmate_grammar.parser.GrammarParser>`
     - .. autodoc2-docstring:: textmate_grammar.parser.GrammarParser
          :summary:
   * - :py:obj:`TokenParser <textmate_grammar.parser.TokenParser>`
     - .. autodoc2-docstring:: textmate_grammar.parser.TokenParser
          :summary:
   * - :py:obj:`MatchParser <textmate_grammar.parser.MatchParser>`
     - .. autodoc2-docstring:: textmate_grammar.parser.MatchParser
          :summary:
   * - :py:obj:`ParserHasPatterns <textmate_grammar.parser.ParserHasPatterns>`
     -
   * - :py:obj:`PatternsParser <textmate_grammar.parser.PatternsParser>`
     - .. autodoc2-docstring:: textmate_grammar.parser.PatternsParser
          :summary:
   * - :py:obj:`BeginEndParser <textmate_grammar.parser.BeginEndParser>`
     - .. autodoc2-docstring:: textmate_grammar.parser.BeginEndParser
          :summary:
   * - :py:obj:`BeginWhileParser <textmate_grammar.parser.BeginWhileParser>`
     - .. autodoc2-docstring:: textmate_grammar.parser.BeginWhileParser
          :summary:

API
~~~

.. py:class:: GrammarParser(grammar: dict, language: textmate_grammar.language.LanguageParser | None = None, key: str = '', is_capture: bool = False, **kwargs)
   :canonical: textmate_grammar.parser.GrammarParser

   Bases: :py:obj:`abc.ABC`

   .. autodoc2-docstring:: textmate_grammar.parser.GrammarParser

   .. rubric:: Initialization

   .. autodoc2-docstring:: textmate_grammar.parser.GrammarParser.__init__

   .. py:method:: initialize(grammar: dict, **kwargs)
      :canonical: textmate_grammar.parser.GrammarParser.initialize
      :staticmethod:

      .. autodoc2-docstring:: textmate_grammar.parser.GrammarParser.initialize

   .. py:method:: parse(handler: textmate_grammar.handler.ContentHandler, starting: textmate_grammar.handler.POS = (0, 0), boundary: textmate_grammar.handler.POS | None = None, **kwargs) -> tuple[bool, list[textmate_grammar.elements.Capture | textmate_grammar.elements.ContentElement], tuple[int, int] | None]
      :canonical: textmate_grammar.parser.GrammarParser.parse

      .. autodoc2-docstring:: textmate_grammar.parser.GrammarParser.parse

   .. py:method:: match_and_capture(handler: textmate_grammar.handler.ContentHandler, pattern: textmate_grammar.handler.Pattern, starting: textmate_grammar.handler.POS, boundary: textmate_grammar.handler.POS, parsers: dict[int, textmate_grammar.parser.GrammarParser] | None = None, parent_capture: textmate_grammar.elements.Capture | None = None, **kwargs) -> tuple[tuple[textmate_grammar.handler.POS, textmate_grammar.handler.POS] | None, str, list[textmate_grammar.elements.Capture | textmate_grammar.elements.ContentElement]]
      :canonical: textmate_grammar.parser.GrammarParser.match_and_capture

      .. autodoc2-docstring:: textmate_grammar.parser.GrammarParser.match_and_capture

.. py:class:: TokenParser(grammar: dict, **kwargs)
   :canonical: textmate_grammar.parser.TokenParser

   Bases: :py:obj:`textmate_grammar.parser.GrammarParser`

   .. autodoc2-docstring:: textmate_grammar.parser.TokenParser

   .. rubric:: Initialization

   .. autodoc2-docstring:: textmate_grammar.parser.TokenParser.__init__

.. py:class:: MatchParser(grammar: dict, **kwargs)
   :canonical: textmate_grammar.parser.MatchParser

   Bases: :py:obj:`textmate_grammar.parser.GrammarParser`

   .. autodoc2-docstring:: textmate_grammar.parser.MatchParser

   .. rubric:: Initialization

   .. autodoc2-docstring:: textmate_grammar.parser.MatchParser.__init__

.. py:class:: ParserHasPatterns(grammar: dict, **kwargs)
   :canonical: textmate_grammar.parser.ParserHasPatterns

   Bases: :py:obj:`textmate_grammar.parser.GrammarParser`, :py:obj:`abc.ABC`

.. py:class:: PatternsParser(grammar: dict, **kwargs)
   :canonical: textmate_grammar.parser.PatternsParser

   Bases: :py:obj:`textmate_grammar.parser.ParserHasPatterns`

   .. autodoc2-docstring:: textmate_grammar.parser.PatternsParser

   .. rubric:: Initialization

   .. autodoc2-docstring:: textmate_grammar.parser.PatternsParser.__init__

.. py:class:: BeginEndParser(grammar: dict, **kwargs)
   :canonical: textmate_grammar.parser.BeginEndParser

   Bases: :py:obj:`textmate_grammar.parser.ParserHasPatterns`

   .. autodoc2-docstring:: textmate_grammar.parser.BeginEndParser

   .. rubric:: Initialization

   .. autodoc2-docstring:: textmate_grammar.parser.BeginEndParser.__init__

.. py:class:: BeginWhileParser(grammar: dict, **kwargs)
   :canonical: textmate_grammar.parser.BeginWhileParser

   Bases: :py:obj:`textmate_grammar.parser.PatternsParser`

   .. autodoc2-docstring:: textmate_grammar.parser.BeginWhileParser

   .. rubric:: Initialization

   .. autodoc2-docstring:: textmate_grammar.parser.BeginWhileParser.__init__
