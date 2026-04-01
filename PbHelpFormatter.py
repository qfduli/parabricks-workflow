"""
A custom help formatter.

The one we've been using would break some lines where they should not be broken.

One example that comes to mind right off is DeepVariant's
--keep-legacy-allele-counter-behavior options which has a URL in it, which
would get broken into "htt", "ps://github.com/google/deepvariant/commit/fbde0674639a28cb9e8" and
"004c7a01bbe25240c7d46".

rna_fq2bam also has an equation that would get broken in the middle of a name.

This formatter also drops the "(default: None)" text.  See _get_help_string() for more details.

NOTE:
    We can continue to print default values like we are, or we can do our own
    custom default text by including "%(default)s" in the help string.  In our
    PBOption() we'd do something like

        PBOption(category='whatever',
            name='-name',
            default=42,
            helpStr="We chose a default of %(default)s because we felt like it")

    and the help string would come out as

        We chose a default of 42 because we felt like it

    And remember to put a period at the end of the sentence.

"""
import argparse
from gettext import gettext as _

class PbHelpFormatter(argparse.ArgumentDefaultsHelpFormatter):
    """
    Use this instead of the argparse.ArgumentDefaultsHelpFormatter.
    """

    def _split_lines(self, text, width):
        """
        Rather than split lines at an arbitrary location, try to be a bit
        intelligent about it.  There's probably some Python library somewhere
        that does a better job, but this is an improvement on the current situation.
        """
        line_list = []
        words = text.split()
        line = ''
        while words:
            # Build a line up to/near the max allowed width.
            while words and len(line) <= width:
                line += f" {words[0]}"
                words.pop(0)
            line_list.append(line)
            line = ''
        return line_list

    # Copied from ArgumentDefaultsHelpFormatter.  Do what they do, only skip "(default: None)".
    def _get_help_string(self, action):
        """
        Add the default value to the option help message.

        ArgumentDefaultsHelpFormatter and BooleanOptionalAction when it isn't
        already present. This code will do that, detecting cornercases to
        prevent duplicates or cases where it wouldn't make sense to the end
        user.
        """
        help = action.help
        if help is None:
            help = ''

        if '%(default)' not in help:
            if action.default is not argparse.SUPPRESS:
                defaulting_nargs = [argparse.OPTIONAL, argparse.ZERO_OR_MORE]
                if action.option_strings or action.nargs in defaulting_nargs:
                    if action.default is not None: # <----------- Added this line.
                        help += _(' (default: %(default)s)')
        return help
