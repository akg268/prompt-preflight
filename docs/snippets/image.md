# Image generation contract

## MD

```md
# Task
Create an image of [specific subject].

# Visual Details
[Subject details: type, color, materials, pose, condition, objects, scene]

# Style
[Photorealistic, cinematic, 3D, watercolor, vector, anime, brand style, mood]

# Output Format
[Aspect ratio, orientation, resolution, transparent background, file type]

# Optional
- Avoid: [text, logos, extra people, clutter, unsafe elements]
- Example/style reference: [image, brand, artist-free visual reference]
- Success criteria: [what should be visually obvious]
```

## XML

```xml
<prompt profile="image">
  <task>Create an image of [specific subject].</task>
  <visual_details>[Subject details: type, color, materials, pose, condition, objects, scene]</visual_details>
  <style>[Photorealistic, cinematic, 3D, watercolor, vector, anime, brand style, mood]</style>
  <output_format>[Aspect ratio, orientation, resolution, transparent background, file type]</output_format>
  <avoid>[Optional: text, logos, extra people, clutter, unsafe elements]</avoid>
  <examples>[Optional image, brand, or style reference]</examples>
</prompt>
```

## TOML

```toml
profile = "image"
task = "Create an image of [specific subject]."
visual_details = "[Subject details: type, color, materials, pose, condition, objects, scene]"
style = "[Photorealistic, cinematic, 3D, watercolor, vector, anime, brand style, mood]"
output_format = "[Aspect ratio, orientation, resolution, transparent background, file type]"
avoid = "[Optional: text, logos, extra people, clutter, unsafe elements]"
examples = "[Optional image, brand, or style reference]"
```
