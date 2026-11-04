-- Merge consecutive code-styled paragraphs into one fenced code block.
--
-- Word has no "code block" object: a listing is one paragraph per line, all
-- carrying the `Kód` (styleId `Kd`) paragraph style. Pandoc's docx reader
-- (with +styles) exposes each as a Div with custom-style="Kód", so without this
-- filter they come out as ordinary paragraphs and the gate cannot tell a code
-- line from prose. This filter turns a run of them into a CodeBlock, matching
-- the fenced block in thesis.typ.

local code_styles = {
  ["Kód"] = true,
  ["Kod"] = true,
}

local function code_line(block)
  if block.t ~= "Div" then
    return nil
  end
  if not code_styles[block.attributes["custom-style"] or ""] then
    return nil
  end
  if #block.content ~= 1 or block.content[1].t ~= "Para" then
    return nil
  end
  return pandoc.utils.stringify(block.content[1])
end

function Blocks(blocks)
  local out = {}
  local i = 1
  while i <= #blocks do
    local line = code_line(blocks[i])
    if line == nil then
      out[#out + 1] = blocks[i]
      i = i + 1
    else
      local lines = {}
      while line ~= nil do
        lines[#lines + 1] = line
        i = i + 1
        line = i <= #blocks and code_line(blocks[i]) or nil
      end
      -- A class keeps pandoc's markdown writer on fenced blocks; the gate
      -- ignores the info string.
      out[#out + 1] = pandoc.CodeBlock(table.concat(lines, "\n"), { "code" })
    end
  end
  return out
end
