# Salma Is on the Line: A Voice Coach That Teaches Seniors to Pay a Bill With Their Phone

*The story of "Learn, Practice, Adopt": built in one hackathon day with Streamlit and open LLMs, then reshaped by our own tests.*

**Try it:** [lpa-digitalpayment.streamlit.app](https://lpa-digitalpayment.streamlit.app/) · **Demo:** [Loom video](https://www.loom.com/share/402d31dce8094bb1ba74e003bd7dfcc9) · **Slides:** [Google Drive](https://drive.google.com/file/d/1lsQj6gRqKqwQcYXNOPLvv_ZwvlPbI0jm/view?usp=drive_link)

---

## The problem

Morocco has about **13.8 million mobile wallet accounts**, each used about **1.4 times a year**. At the end of the month, bill-payment offices are still full of people, many of them older, with a paper bill and cash.

What holds them back isn't technology. It's **literacy and trust**: *"What if I press the wrong button and lose my money?"*, *"Should I give this SMS code to someone?"*, *"Where is the number they ask for?"*

What they need is someone patient beside them the first time. So we built a phone call.

## The idea: learn it inside a call

On screen there is only a fictional wallet, *Mahfadati*, with 500 MAD of fake money and a paper electricity bill. On the line is **Salma**, a calm voice coach. Everything happens in that one call:

1. **Consent, by voice.** It's anonymous, the money is fake and the voice is never recorded. The user just says *"oui"*.
2. **Assisted mode: explain a concept, then use it right away.** The concepts are paying by phone, the bill reference, checking before paying and the SMS code (*"a key sent only to you"*). While you apply each one, Salma points at the right element with a yellow outline.
3. **Try alone.** *"I'm still on the line if you need me."* After 20 seconds of hesitation she gently relaunches you. After two slips, she offers one more guided round.
4. **The value moment.** *Two minutes from home, instead of a trip and a queue.*
5. **Five short questions**: understood? able to do it alone next time? feel safe with the SMS code? hardest step? will you try with a real bill?

A **provider dashboard** turns these anonymous sessions into decisions.

## How it works

- **The stack:** Streamlit, SQLite, one `openai` client for all LLMs, Groq Whisper for listening and gTTS for Salma's voice. It is deployed on Streamlit Community Cloud.
- **The coach:** Groq `gpt-oss-20b` answers first, with NVIDIA `mistral-nemotron` as backup. On our first live test it answered in **744 ms**. NVIDIA `nemotron-3-super-120b` analyses each finished session in the background (about **11.7 s**).
- **Salma "sees" the screen.** Each call describes the screen in words: the visible elements with their ids, what the user just did, and how many mistakes they made. The model must answer `{"say": "...", "highlight": "bill_ref"}`: one field is spoken, the other points at the element.
- **She never goes silent.** Providers are tried in order with an 8-second timeout each, then a pre-written answer for the screen. A short filler (*"Hmm, un instant…"*) plays while the AI thinks. We strip reasoning text, markdown and emoji before anything is spoken.
- **Fixed lines are pre-recorded.** The greeting, the concepts and the instructions are recorded once, so the LLM is only used where it adds value: answering *your* question about *your* screen.

## What our own tests changed

- **"The page is overloaded."** Our first version showed the whole conversation as a written transcript, plus audio players, a text box and a mic button. We removed everything that wasn't the payment app. Salma is **heard, not read**. Only a small call bar stays on top: avatar, call duration, status and *Hang up*.
- **"It should be one call, not a mic button."** So we moved to continuous listening: you just talk.
- **"Salma doesn't hear me."** The browser's built-in speech recognition silently failed on the tester's machine. We replaced it with our own listening: the page measures the volume, records a phrase when someone speaks, stops after about 0.9 s of silence and sends it to Groq Whisper. The audio is then dropped. This works in any modern browser, and the mic pauses while Salma speaks.
- **"The screens are mixed."** The old screen lingered under the new one while Salma's voice was generated. Now each screen replaces the previous one as a whole, and the voice comes after the screen is drawn.
- **"Start the call before the questions."** Nervous users may need help from the very first screen, so the call now starts first.

None of these were technical breakthroughs. All of them came from one lesson: **the product is the experience of a nervous first-timer.**

## A dashboard that earns its numbers

Our first dashboard showed a lot and said little. The rebuilt one answers a single question: *what should the wallet team fix next?*

- **Four figures:** who pays alone after one session, how much less help people need on the 2nd attempt, the screen that still blocks people when they're alone, and abandons.
- **One chart:** difficulty per screen on the 1st attempt (with Salma) versus the 2nd (alone). *What drops is learned with Salma; what stays high must be fixed in the app.*
- **What people say versus what they did:** *"2 of 3 say they can do it alone, and those 2 really did it without help."*
- **At most three AI recommendations**, with two rules enforced in code. **No number, no recommendation.** And small samples are reported honestly: "3 of 5", not "60%", with confidence set to "low" under 10 sessions.

## Next steps

- **Darija.** Every text already lives in one file, keyed by language.
- **Real pilots** with a wallet provider and senior associations.
- **Letting users interrupt Salma**, like in a real call.
- **Persistent storage.**

## The takeaway

The most useful thing AI did here wasn't generating text. It was being **patient at scale**: answering *"where is the number?"* for the fifth time in the same calm voice, pointing at the right spot, and noticing when someone froze. Then it turned those moments into evidence a product team can act on.

Financial inclusion doesn't start with a new app. It starts with a first payment that didn't feel scary.

---

*Built at the GOMYCODE "Come Build with AI" hackathon, September 2026 · Python, Streamlit, SQLite, Groq, NVIDIA Build, gTTS · Coded with the help of Claude Code.*
