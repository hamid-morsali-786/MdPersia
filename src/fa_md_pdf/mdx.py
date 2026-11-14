"""Static MDX reading through the existing Markdown engine, without evaluating JS."""
import re

MDX_NOTICE = (
    "پیش‌نمایش ایستای MDX — بخش Markdown نمایش داده می‌شود؛ "
    "کدهای import/export، JSX و عبارت‌های JavaScript به‌صورت متن حفظ می‌شوند."
)


def static_mdx_plugin(md):
    # JSX is source text here. It must never become an active HTML element,
    # fetch an imported module, or disappear as an unknown component.
    md.options["html"] = False
    md.options["typographer"] = False

    def module_source(state, start_line, end_line, silent):
        if state.level != 0 or state.is_code_block(start_line):
            return False
        start = state.bMarks[start_line] + state.tShift[start_line]
        line = state.src[start:state.eMarks[start_line]]
        if not re.match(r"(?:import\s|export\s+(?:default\b|const\b|let\b|var\b|"
                        r"function\b|async\b|class\b|type\b|interface\b|[{*]))", line):
            return False
        if silent:
            return True
        # An ESM source paragraph is shown literally. No JS parser or runtime
        # is needed, including for incomplete imports while editing.
        next_line = start_line + 1
        while next_line < end_line and not state.isEmpty(next_line):
            next_line += 1
        token = state.push("fence", "code", 0)
        token.info = "javascript"
        token.content = state.getLines(start_line, next_line, state.blkIndent, False)
        token.map = [start_line, next_line]
        state.line = next_line
        return True

    md.block.ruler.before("paragraph", "mdx_module_source", module_source)
