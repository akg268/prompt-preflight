# Task
[Specific action to perform]

# Context
[Relevant background, files, source material, data, links, or constraints]

# Output Format
[Exact structure: bullets, table, JSON, patch, report, image specs, etc.]

# Success Criteria
- [How the agent should verify the result]
- [What must be true when the work is done]

# Optional
- Constraints: [boundaries or things to preserve]
- Examples: [sample output or style reference]
- Non-goals: [what not to do]
import re
from pathlib import Path

content = Path('src/prompt_preflight/analyzer.py').read_text()

# Find the literal backslash-n and replace it
content = content.replace("def _is_enabled\\(cat: str\\) -> bool:\\n        return config\\.policy_for\\(cat\\) != \\\"disable\\\" if config else True\\n", "")

# We also need to add it properly
proper_helper = """
    def _is_enabled(cat: str) -> bool:
        return config.policy_for(cat) != "disable" if config else True
"""
content = content.replace("    text = \" \".join(raw_prompt.split())", "    text = \" \".join(raw_prompt.split())" + proper_helper)

Path('src/prompt_preflight/analyzer.py').write_text(content)
print("Done fixing syntax")
