Reference catalog for succinct Part 3. Read it before you write or edit technical documentation, procedures, or API references.

# Part 3: Write plain (Simplified Technical English)

Apply to technical text: procedures, docs, READMEs, API references, runbooks, error explanations. The goal of STE is that the reader understands each sentence on first reading. The controlled dictionary is not reproduced here; these rules summarize Part 1 of ASD-STE100 Issue 9 for everyday technical writing.

## Words

1. One word, one meaning, one part of speech. Prefer the simple, frequent word. Recurrent replacements:
   - perform, accomplish, carry out -> do
   - ensure -> make sure
   - utilize -> use
   - may -> can; shall, should -> must (requirements) or imperative (steps)
   - acceptable -> permitted
   - avoid -> prevent
   - however -> but
   - since, as (causal) -> because
   - therefore -> thus, as a result
   - rotate -> turn; press -> push; insert -> put; fit -> install; prior to -> before; utilize -> use
2. No phrasal verbs. Two approved words must not make a new meaning: "put out the fire" becomes "extinguish the fire"; "give off fumes" becomes "release fumes". No Latin abbreviations: write "for example", "that is", not "e.g.", "i.e.", "etc.".
3. Verbs act; nouns sit. Describe actions with verbs: "Before you remove the unit", not "Before the removal of the unit". Do not shift parts of speech: "check" as a noun gets "do a check of"; "damage" as a noun gets "cause damage to"; "test" as a verb gets "do a test of".
4. One term per item. Pick one technical noun for each thing and keep it for the whole text. Do not alternate synonyms: the "actuator" stays "actuator", never drifts to "control unit" or "servo". Write code identifiers exactly as the code writes them, every time.
5. No slang, jargon, or regional words as terms: "brick the router" becomes "set the router to OFF"; "gear" becomes "tools and equipment". American spelling, unless the project's style says otherwise.
6. Multi-word nouns of three words or fewer. Longer: add "of" ("calibration of the resistance of the runway light connection"), hyphenate only directly related words, or write the full term once and use a short form after.

## Verbs

7. Active voice. In instructions, imperative: "Adjust the temperature", not "The temperature must be adjusted". Passive only in descriptions when the agent is unknown and it matters ("During transmission, the data was corrupted").
8. Simple forms only: infinitive, imperative, simple present, simple past, simple future, and the past participle as an adjective ("the disassembled unit"). No present perfect ("has adjusted"), no progressive ("is adjusting"), no auxiliary stacking, no "-ing" chains: "When you do this procedure", not "When you are doing this procedure". Name the actor: "you" for the reader, "we" for your side.

## Sentences

9. Maximum 20 words in a step, 25 words in description. One instruction per sentence unless actions occur at the same time. No semicolons; write two sentences.
10. Keep every word: no dropped subjects ("If the shims are installed", not "If installed"), no contractions ("do not", not "don't"), keep articles ("Turn the shaft assembly"), keep "that" ("Make sure that the valve is open").
11. Conditions first, comma, then command: "When the light comes on, set the switch to NORMAL." The reader must know the condition before the action.
12. Vertical lists for anything complex: colon at the end of the intro, one item per line, each item capitalized, a period only on full sentences, no commas or semicolons at item ends, no nesting inside items. Cap visible lists at 5 items (Part 1, rule 9); split into "now" and "later".
13. Paragraphs: topic sentence first, one topic per paragraph, six sentences maximum. Headings in sentence case, no emojis or arrows.

## Safety and limits

14. Notes and asides give information, never instructions. If the information prevents damage or injury, it belongs in the instruction itself. Destructive-action warnings: command or condition first, then the concrete risk. "Warning" for risk of injury or data loss; "caution" for damage to things; if both, warning. ("Before you close the hatch, make sure that no persons are in the compartment. When the hatch is closed, there is no airflow and there is a risk of suffocation.")
15. Remove ambiguity: give "this" and "it" one clear referent or name the noun; read "with" sentences twice ("Install the panel with the green fasteners" has three meanings); give units with numbers ("10 mA", "2 hours"); count parentheses text, numbers, units, abbreviations, and quoted UI strings as one word each.

## Quoted text

Code, identifiers, UI strings, log lines, and anything in quotation marks is quoted text. Copy it exactly. Do not "improve" its spelling, capitalization, or punctuation, and do not count it against sentence length.
