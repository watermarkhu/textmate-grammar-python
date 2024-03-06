:py:mod:`textmate_grammar.logger`
=================================

.. py:module:: textmate_grammar.logger

.. autodoc2-docstring:: textmate_grammar.logger
   :allowtitles:

Module Contents
---------------

Classes
~~~~~~~

.. list-table::
   :class: autosummary longtable
   :align: left

   * - :py:obj:`LogFormatter <textmate_grammar.logger.LogFormatter>`
     - .. autodoc2-docstring:: textmate_grammar.logger.LogFormatter
          :summary:
   * - :py:obj:`Logger <textmate_grammar.logger.Logger>`
     - .. autodoc2-docstring:: textmate_grammar.logger.Logger
          :summary:

Functions
~~~~~~~~~

.. list-table::
   :class: autosummary longtable
   :align: left

   * - :py:obj:`track_depth <textmate_grammar.logger.track_depth>`
     - .. autodoc2-docstring:: textmate_grammar.logger.track_depth
          :summary:

Data
~~~~

.. list-table::
   :class: autosummary longtable
   :align: left

   * - :py:obj:`MAX_LENGTH <textmate_grammar.logger.MAX_LENGTH>`
     - .. autodoc2-docstring:: textmate_grammar.logger.MAX_LENGTH
          :summary:
   * - :py:obj:`LOGGER <textmate_grammar.logger.LOGGER>`
     - .. autodoc2-docstring:: textmate_grammar.logger.LOGGER
          :summary:

API
~~~

.. py:data:: MAX_LENGTH
   :canonical: textmate_grammar.logger.MAX_LENGTH
   :value: 79

   .. autodoc2-docstring:: textmate_grammar.logger.MAX_LENGTH

.. py:function:: track_depth(func)
   :canonical: textmate_grammar.logger.track_depth

   .. autodoc2-docstring:: textmate_grammar.logger.track_depth

.. py:class:: LogFormatter(fmt=None, datefmt=None, style='%', validate=True, *, defaults=None)
   :canonical: textmate_grammar.logger.LogFormatter

   Bases: :py:obj:`logging.Formatter`

   .. autodoc2-docstring:: textmate_grammar.logger.LogFormatter

   .. rubric:: Initialization

   .. autodoc2-docstring:: textmate_grammar.logger.LogFormatter.__init__

   .. py:attribute:: green
      :canonical: textmate_grammar.logger.LogFormatter.green
      :value: '\x1b[32;32m'

      .. autodoc2-docstring:: textmate_grammar.logger.LogFormatter.green

   .. py:attribute:: grey
      :canonical: textmate_grammar.logger.LogFormatter.grey
      :value: '\x1b[38;20m'

      .. autodoc2-docstring:: textmate_grammar.logger.LogFormatter.grey

   .. py:attribute:: yellow
      :canonical: textmate_grammar.logger.LogFormatter.yellow
      :value: '\x1b[33;20m'

      .. autodoc2-docstring:: textmate_grammar.logger.LogFormatter.yellow

   .. py:attribute:: red
      :canonical: textmate_grammar.logger.LogFormatter.red
      :value: '\x1b[31;20m'

      .. autodoc2-docstring:: textmate_grammar.logger.LogFormatter.red

   .. py:attribute:: bold_red
      :canonical: textmate_grammar.logger.LogFormatter.bold_red
      :value: '\x1b[31;1m'

      .. autodoc2-docstring:: textmate_grammar.logger.LogFormatter.bold_red

   .. py:attribute:: reset
      :canonical: textmate_grammar.logger.LogFormatter.reset
      :value: '\x1b[0m'

      .. autodoc2-docstring:: textmate_grammar.logger.LogFormatter.reset

   .. py:attribute:: format_string
      :canonical: textmate_grammar.logger.LogFormatter.format_string
      :value: '%(name)s:%(message)s'

      .. autodoc2-docstring:: textmate_grammar.logger.LogFormatter.format_string

   .. py:attribute:: FORMATS
      :canonical: textmate_grammar.logger.LogFormatter.FORMATS
      :value: None

      .. autodoc2-docstring:: textmate_grammar.logger.LogFormatter.FORMATS

   .. py:method:: format(record)
      :canonical: textmate_grammar.logger.LogFormatter.format

      .. autodoc2-docstring:: textmate_grammar.logger.LogFormatter.format

.. py:class:: Logger(**kwargs)
   :canonical: textmate_grammar.logger.Logger

   .. autodoc2-docstring:: textmate_grammar.logger.Logger

   .. rubric:: Initialization

   .. autodoc2-docstring:: textmate_grammar.logger.Logger.__init__

   .. py:attribute:: long_msg_div
      :canonical: textmate_grammar.logger.Logger.long_msg_div
      :value: '\x1b[1;32m ... \x1b[0m'

      .. autodoc2-docstring:: textmate_grammar.logger.Logger.long_msg_div

   .. py:method:: configure(parser: textmate_grammar.parser.GrammarParser, height: int, width: int, **kwargs) -> None
      :canonical: textmate_grammar.logger.Logger.configure

      .. autodoc2-docstring:: textmate_grammar.logger.Logger.configure

   .. py:method:: format_message(message: str, parser: typing.Optional[textmate_grammar.parser.GrammarParser] = None, position: tuple[int, int] | None = None, depth: int = 0) -> str
      :canonical: textmate_grammar.logger.Logger.format_message

      .. autodoc2-docstring:: textmate_grammar.logger.Logger.format_message

   .. py:method:: debug(*args, **kwargs) -> None
      :canonical: textmate_grammar.logger.Logger.debug

      .. autodoc2-docstring:: textmate_grammar.logger.Logger.debug

   .. py:method:: info(*args, **kwargs) -> None
      :canonical: textmate_grammar.logger.Logger.info

      .. autodoc2-docstring:: textmate_grammar.logger.Logger.info

   .. py:method:: warning(*args, **kwargs) -> None
      :canonical: textmate_grammar.logger.Logger.warning

      .. autodoc2-docstring:: textmate_grammar.logger.Logger.warning

   .. py:method:: error(*args, **kwargs) -> None
      :canonical: textmate_grammar.logger.Logger.error

      .. autodoc2-docstring:: textmate_grammar.logger.Logger.error

   .. py:method:: critical(*args, **kwargs) -> None
      :canonical: textmate_grammar.logger.Logger.critical

      .. autodoc2-docstring:: textmate_grammar.logger.Logger.critical

.. py:data:: LOGGER
   :canonical: textmate_grammar.logger.LOGGER
   :value: 'Logger(...)'

   .. autodoc2-docstring:: textmate_grammar.logger.LOGGER
