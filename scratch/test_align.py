from scripts.props_builder import PropsBuilder

builder = PropsBuilder()
characters = list("Hello [whispers] world")
# Mock timestamps
start_times = [float(i) for i in range(len(characters))]
end_times = [float(i) + 0.5 for i in range(len(characters))]

words = builder.align_words(characters, start_times, end_times, "Hello [whispers] world")
print("Words found:", [w["text"] for w in words])

# Check for brackets
has_brackets = any("[" in w["text"] or "]" in w["text"] for w in words)
if has_brackets:
    print("FAILED: Brackets found in subtitles!")
else:
    print("PASSED: No brackets in subtitles.")
