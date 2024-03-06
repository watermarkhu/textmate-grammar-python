:py:mod:`textmate_grammar.language`
===================================

.. py:module:: textmate_grammar.language

.. autodoc2-docstring:: textmate_grammar.language
   :allowtitles:

Module Contents
---------------

Classes
~~~~~~~

.. list-table::
   :class: autosummary longtable
   :align: left

   * - :py:obj:`DummyParser <textmate_grammar.language.DummyParser>`
     - .. autodoc2-docstring:: textmate_grammar.language.DummyParser
          :summary:
   * - :py:obj:`LanguageParser <textmate_grammar.language.LanguageParser>`
     - .. autodoc2-docstring:: textmate_grammar.language.LanguageParser
          :summary:

Data
~~~~

.. list-table::
   :class: autosummary longtable
   :align: left

   * - :py:obj:`LANGUAGE_PARSERS <textmate_grammar.language.LANGUAGE_PARSERS>`
     - .. autodoc2-docstring:: textmate_grammar.language.LANGUAGE_PARSERS
          :summary:

API
~~~

.. py:data:: LANGUAGE_PARSERS
   :canonical: textmate_grammar.language.LANGUAGE_PARSERS
   :value: None

   .. autodoc2-docstring:: textmate_grammar.language.LANGUAGE_PARSERS

.. py:class:: DummyParser()
   :canonical: textmate_grammar.language.DummyParser

   Bases: :py:obj:`textmate_grammar.parser.GrammarParser`

   .. autodoc2-docstring:: textmate_grammar.language.DummyParser

   .. rubric:: Initialization

   .. autodoc2-docstring:: textmate_grammar.language.DummyParser.__init__

.. py:class:: LanguageParser(grammar: dict, **kwargs)
   :canonical: textmate_grammar.language.LanguageParser

   Bases: :py:obj:`textmate_grammar.parser.PatternsParser`

   .. autodoc2-docstring:: textmate_grammar.language.LanguageParser

   .. rubric:: Initialization

   .. autodoc2-docstring:: textmate_grammar.language.LanguageParser.__init__

   .. py:method:: parse_file(filePath: str | pathlib.Path, **kwargs) -> textmate_grammar.elements.Capture | textmate_grammar.elements.ContentElement | None
      :canonical: textmate_grammar.language.LanguageParser.parse_file

      .. autodoc2-docstring:: textmate_grammar.language.LanguageParser.parse_file

   .. py:method:: parse_string(input: str, **kwargs)
      :canonical: textmate_grammar.language.LanguageParser.parse_string

      .. autodoc2-docstring:: textmate_grammar.language.LanguageParser.parse_string
