# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""
Template notebooklet.

Notebooklet modules have three main sections:

- **Result class definition**:
  This defines the attributes and descriptions of the data that you
  want to return from the notebooklet.
- **Notebooklet class definition**:
  This is the entry point for running the notebooklet. At minimum
  it should be a class derived from Notebooklet that implements
  a `run` method and returns your result class.
- **Functions**:
  These do most of the work of the notebooklet and usually the code
  that is copied from or adapted from the original notebook.

Having the latter section is optional. You can choose to implement
this functionality in instance methods of the notebooklet class.

However, there are advantages to keeping these as separate functions
outside the class. It means that all the data used in the functions
has to be passed around as parameters and return values. This can
improve the clarity of the code and reduce errors due to some
dependency on some mysterious global state.

If the user of your notebooklet wants to import the module's code
into a notebook to read and possibly adapt it, having standalone
functions will make it easier from them understand and work with
the code.

"""
from typing import Any, Optional, Iterable, Union, Dict

import attr
from bokeh.plotting.figure import Figure
import pandas as pd
from msticpy.nbtools import nbdisplay

# Note - when moved to the final location (e.g.
# nb/environ/category/mynotebooklet.py)
# you will need to change the "..." to "...." in these
# imports because the relative path has changed.
from ...common import (
    TimeSpan,
    MsticnbMissingParameterError,
    nb_data_wait,
    nb_print,
    set_text,
    nb_markdown,
)

# change the "..." to "...."
from ...notebooklet import Notebooklet, NotebookletResult, NBMetadata
from ... import nb_metadata

# change the ".." to "...."
from ..._version import VERSION

__version__ = VERSION
__author__ = "Your name"


# Read module metadata from YAML
_CLS_METADATA: NBMetadata
_CELL_DOCS: Dict[str, Any]
_CLS_METADATA, _CELL_DOCS = nb_metadata.read_mod_metadata(__file__, __name__)


# pylint: disable=too-few-public-methods
# Rename this class
@attr.s(auto_attribs=True)
class TemplateResult(NotebookletResult):
    """
    Template Results.

    Attributes
    ----------
    all_events : pd.DataFrame
        DataFrame of all raw events retrieved.
    plot : bokeh.models.LayoutDOM
        Bokeh plot figure showing the account events on an
        interactive timeline.
    additional_info: dict
        Additional information for my notebooklet.

    """

    description: str = "Windows Host Security Events"

    # Add attributes as needed here.
    # Make sure they are documented in the Attributes section
    # above.
    all_events: pd.DataFrame = None
    plot: Figure = None
    additional_info: Optional[dict] = None


# pylint: enable=too-few-public-methods


# Rename this class
class TemplateNB(Notebooklet):
    """
    Template Notebooklet class.

    Detailed description of things this notebooklet does:

    - Fetches all events from XYZ
    - Plots interesting stuff
    - Returns extended metadata about the thing

    Document the options that the Notebooklet takes, if any,
    Use these control which parts of the notebooklet get run.

    """

    # assign metadata from YAML to class variable
    metadata = _CLS_METADATA
    __doc__ = nb_metadata.update_class_doc(__doc__, metadata)
    _cell_docs = _CELL_DOCS

    # @set_text decorator will display the title and text every time
    # this method is run.
    # The key value refers to an entry in the `output` section of
    # the notebooklet yaml file.
    @set_text(docs=_CELL_DOCS, key="run")
    def run(
        self,
        value: Any = None,
        data: Optional[pd.DataFrame] = None,
        timespan: Optional[TimeSpan] = None,
        options: Optional[Iterable[str]] = None,
        **kwargs,
    ) -> TemplateResult:
        """
        Return XYZ summary.

        Parameters
        ----------
        value : str
            Host name - The key for searches - e.g. host, account, IPaddress
        data : Optional[pd.DataFrame], optional
            Alternatively use a DataFrame as input.
        timespan : TimeSpan
            Timespan for queries
        options : Optional[Iterable[str]], optional
            List of options to use, by default None.
            A value of None means use default options.
            Options prefixed with "+" will be added to the default options.
            To see the list of available options type `help(cls)` where
            "cls" is the notebooklet class or an instance of this class.

        Returns
        -------
        TemplateResult
            Result object with attributes for each result type.

        Raises
        ------
        MsticnbMissingParameterError
            If required parameters are missing

        """
        # This line use logic in the superclass to populate options
        # (including default options) into this class.
        super().run(
            value=value, data=data, timespan=timespan, options=options, **kwargs
        )

        if not value:
            raise MsticnbMissingParameterError("value")
        if not timespan:
            raise MsticnbMissingParameterError("timespan.")

        # Create a result class
        result = TemplateResult()
        result.description = self.metadata.description
        result.timespan = timespan

        # You might want to always do some tasks irrespective of
        # options sent
        all_events_df = _get_all_events(
            self.query_provider, host_name=value, timespan=timespan
        )
        result.all_events = all_events_df

        if "plot_events" in self.options:
            result.plot = _display_event_timeline(acct_event_data=all_events_df)

        if "get_metadata" in self.options:
            result.additional_info = _get_metadata(host_name=value, timespan=timespan)

        # Assign the result to the _last_result attribute
        # so that you can get to it without having to re-run the operation
        self._last_result = result  # pylint: disable=attribute-defined-outside-init

        return self._last_result

    # You can add further methods to do things after (or before) the main
    # run method. You might need these if you want to add an interaction
    # point where the user needs to select and option. For example, you
    # could have a "select_account" method that uses a widget to let the
    # notebook user pick from a list. Then have a follow on method that
    # does something with this choice.
    def run_additional_operation(
        self, event_ids: Optional[Union[int, Iterable[int]]] = None
    ) -> pd.DataFrame:
        """
        Addition method.

        Parameters
        ----------
        event_ids : Optional[Union[int, Iterable[int]]], optional
            Single or interable of event IDs (ints).

        Returns
        -------
        pd.DataFrame
            Results with expanded columns.

        """
        # Include this to check the "run()" has happened before this method
        # can be run
        if (
            not self._last_result or self._last_result.all_events is None
        ):  # type: ignore
            print(
                "Please use 'run()' to fetch the data before using this method.",
                "\nThen call 'expand_events()'",
            )
            return None
        # Print a status message - this will not be displayed if
        # the user has set the global "verbose" option to False.
        nb_print("We maybe about to wait some time")

        nb_markdown("Print some message that always displays", "blue, bold")
        return _do_additional_thing(
            evt_df=self._last_result.all_events,  # type: ignore
            event_ids=event_ids,
        )
        # Note you can also assign new items to the result class in
        # self._last_result and return the updated result class.


# This section contains functions that do the work. It can be split into
# cells recognized by some editors (like VSCode) but this is optional

# %%
# Get Windows Security Events
def _get_all_events(qry_prov, host_name, timespan):
    # Tell the user that you're fetching data
    # (doesn't display if nb.set_opt("silent", True))
    nb_data_wait("SecurityEvent")
    return qry_prov.WindowsSecurity.list_host_events(
        timespan,
        host_name=host_name,
        add_query_items="| where EventID != 4688 and EventID != 4624",
    )


# You can add title and/or text to individual functions as they run.
# You can reference text from sections in your YAML file or specify
# it inline (see later example)
@set_text(docs=_CELL_DOCS, key="display_event_timeline")
def _display_event_timeline(acct_event_data):
    # Plot events on a timeline

    # Note the nbdisplay function is a wrapper around IPython.display()
    # However, it honors the "silent" option (global or per-notebooklet)
    # which allows you to suppress output while running.
    return nbdisplay.display_timeline(
        data=acct_event_data,
        group_by="EventID",
        source_columns=["Activity", "Account"],
        legend="right",
    )


# This function has no text output associated with it
def _get_metadata(host_name, timespan):
    return {
        "host": host_name,
        "data_items": {"age": 97, "color": "blue", "country_of_origin": "Norway"},
        "provider": "whois",
        "time_duration": timespan,
    }


# %%
# Extract event details from events
# Note using inline text output here - usually better to store this
# all in the yaml file for maintainability.
@set_text(
    title="Do something else",
    hd_level=3,
    text="""
This may take some time to complete for large numbers of events.

It will do:
- Item one
- Item two
""",
    md=True,
)
def _do_additional_thing(evt_df, event_ids):
    # nb_print is the same as print() except it honors the
    # 'silent' option.
    nb_print("Doing something time-consuming...")
    return evt_df[evt_df["EventID"].isin(event_ids)]
