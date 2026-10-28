# Northstar — the goal

**Status: authoritative. This file overrides every other document in this repo.**
Every research, design, review and build step reads this file first and is checked against it before it is accepted.
Last confirmed with the user: 2026-10-28. Later answers (§1, §2) take precedence over earlier ones: those of 2026-10-28 first, then 2026-10-27, 2026-10-25, 2026-10-24, 2026-10-15, 2026-10-14, 2026-10-10, 2026-10-09 and 2026-10-08.

---

## 1. In the user's words

Quoted verbatim from the conversation of 2026-10-07, after the user rejected the first design:

> "So what I want is a solution. a system, not a learning lessons for me. What I want is I want a very architecturally system / design system, potentially two architecture one for human one for the AI."

> "So for human, I should sort of have like a structural memory of what to learn, and then all what you are giving me, the short record of what I hold and weekly 20 minute sections, those are just the way I use it / a human use it. So at the end of the day, it is not the solution I'm looking for."

> "To build for AI, this is more about like a well architected memory solution as well. Because right now, all the AI chat sort of lost its focus after a long sections, and it's drifting away from both AI knowledge and also from human knowledge as well. So I need a system that does that."

> "Potentially this can be useful for let's say Claude or ChatGPT as well, because this is going to be their memory system, not just the Claude.md etc, it is a system not just memory files, which ideally I wanted to provide a better experience. Let's say from a long chat to generated answer is still focusing on my goal. With this memory architecture/system."

> "Something I feel like you are missing is that not just what I learned, but also what AI told me, taught me. So, so that means is what I said, also what AI said. So, of course, everything these needs to be managed by an AI. But of course, again, it's like the self-convolute part where you have an agent that might lost its attention helping you manage the system which you're trying to build for such a case."

On 2026-10-08, answering the round-2 research questions, the user said (verbatim):

> "If this is hard, I dont mind doing it on Claude Desktop chat or ChatGPT desktop chat, or the code (ideally both chat and code for both product)"

> "Personal accounts mainly, will be great for enterprise as well."

> "Local and cloud both available, cloud potentially for future and local for current."

> "How well is again about how people use it, you are drifted again, the key is to help human understand and remember their knowledge, just like textbooks."

> "Should be product agnostic right? It is all about connectors when it comes to ChatGPT or Claude right? The system is agnostic, it is for any AI agent/LLM."

On 2026-10-09, after reading the design's `ARCHITECTURE.md` (sections after §9 skimmed), the user commented (verbatim):

> "1. Platform support: The system should not assume that I will always use a Mac. Ideally, it should work on both Mac and Windows. Treat this as a strong preference, assess the platform dependencies, and explain any limitations or tradeoffs."

> "2. Connectors — an architectural question: Does Northstar need a separate product-specific connector for every application, or could a shared integration approach, such as MCP, provide the required capabilities? I am comfortable with separate connectors where they are necessary or more effective. I am not mandating MCP or rejecting product-specific development. Evaluate the alternatives by their actual effectiveness, especially capture, in-session focus, and cross-session continuity."

> "3. Knowledge organization — integration, subdivision, and consolidation: New material should connect to relevant existing knowledge. Sometimes it should extend an existing section; sometimes a topic becomes detailed enough, or develops a distinct thread, to deserve its own subsection or branch. Related branches should also be able to merge or be summarized at a broader level. Can the proposed methodology support this evolution in both directions? Explain how it decides where new material belongs and when to subdivide or consolidate. This is a question about the methodology, rather than a prescribed implementation."

> "4. Personal relevance and “what to learn”: The memory system should center on my evolving ideas, viewpoints, reasoning, interests, and questions or problems I want to explore—including understanding developed through conversations with AI. Generic information that I can readily search for, such as “What is an LLM?”, should not automatically become something to organize or a learning gap merely because the term appeared without an explanation. Use personal relevance as the distinction, rather than simply subjective versus objective content. Objective information can matter when it directly supports my thinking or problems. Explain how the design keeps the system focused on my intellectual development instead of turning it into a generic encyclopedia or glossary."

> "5. Evaluation — establish a baseline and measure improvement: Establish and measure a baseline without Northstar first, then compare it with performance using Northstar. Use comparable scenarios and define what improvement means. The initial benchmark does not need the rigor or specificity of a SWE-style benchmark, but it should provide meaningful measurements rather than rely only on impressions. Propose a manageable initial benchmark covering both AI assistance and the usefulness of the human-facing knowledge organization."

> "6. Deliverable and approval: Return the revised proposal, a concise explanation of the major changes, and any unresolved questions or tradeoffs. Keep this work at the proposal and evaluation-plan stage, following the existing approval process."

Answering follow-up questions the same day (verbatim):
- Will Northstar be used on more than one computer, sharing one memory? > "Most likely many machines, and potentially for phones as well"
- Platform order for the first evaluated prototype? > "I would say windows first, iOS second, Mac last (But technically pretty close in terms of their ranking)"
- May the human-side benchmark include a short one-off session with the user before and after? > "Short sessions OK"
- What should the benchmark scenarios be built from? > "My real topics"

On 2026-10-10, after reviewing the revised proposal through an interactive review page, the user wrote (verbatim):

> "1. So a lot of things, it sounds like you have very hard-coded rules. For example, when to integrate, etc. And when to subdivide it, you set 8 or 4, these sounds like very hard-coded rules. And not just for this section, it's like across everything, it sounds like hard-coded. Would it better to be more dynamic?"

> "2. Secondly, like the methodology, like how AI works, makes sense. just by looking at it, but not sure if that actually works on um, on the real side. So, like you're just like pasting the context. I think that should work for if you're pasting the relevant context, not just like general context. The relevant context based on the conversations."

> "3. About the examples for the personal relevance. I think the most common cases is where like let's say I ask the question "how should my memory system keep and like how I am focused in a long chat?", the AI replied but then I probably don't agree with what AI said. So in at this case nothing should be recorded yet. But then, until I make a statement, or ask a follow up question, and you sort of can learn that where my head is going at, then you start recording. Just like right now my typing, I'm saying all these words, and these are my opinions, and of course, you only record them when they are correct. Like when you when you research and teach me back, it is correct. But then if I just ask any question, not all the answer from AI needs to be recorded."

> "4. The knowledge book again has some sort of issue like that as well. You're putting all, first of all, it's too long to read. Secondly, you know, I'm not necessarily wanted all the AI explanations. I just want the ideas. You know, to connect the dots. For example, I let's say I have many chats sections that about What's the approach to build an agent on in an interview or even in real life? So, of course, when I'm building in real life, I will have my own way of building it. But then when I'm learning something in that only builds agents in an interview, you know, of course, I might have something that's a conflict of what I used to learn. So in this case, the book should be have what I have learned from like an actual development, you know, For example, I always love to start with workflows and then eventually build out the build out the agents because right now if we build the orchestration, etc. So then maybe there's a powerful model coming out and then All my work would just gone in vain. For building a workflow, it preserved my work. At least it's, it's, it's an artifact that can be more durable to like changes of generic solution out there. So this is my ideas and you know, this is what I have learned. What I have to tell the AI and come up with my conclusions. But not necessarily this applies in an interview. So when I'm preparing for an interview, I might forget about my previous idea like this. So I think this is what to be stored instead of like a, the book that you describing. Like you're describing again, like knowledge, but it's still like not my knowledge, not my, not the stuff I really learned."

> On DQ-15 (views in new chats): "I think it is relevant to my ideas on the top, only when it is very linked, not just simply linked or mentioned." On DQ-17 (Book and relevance defaults): "Check the above ideas". Every other open decision: "go with the recommendation".

> "Again, all these are just recommendations, okay? Not hard requirements. So you should have deep research and reason on yourself because what I said might not make sense or might just oversimplify from what you're giving me."

Answering follow-up questions the same day (verbatim):
- Is the unit of memory the user's idea (principle, conclusion, approach, position, open question, tension) with its why, where it applies, how they got there and its connections, and the Book a short map of it with depth on click? > "Yes but also not just ideas, it has to be validated by the discussion or research with AI, so maybe calling them knowledge will be more appropriate."
- How should AI-said content be treated? > "Adopted = first-class; rest archived" (what AIs taught that the user agreed with, built on or used is first-class and attributed; other AI answers stay only in a private, searchable raw archive, never shown or injected on their own).
- Order of work? > "Probe first, then revise": test the riskiest assumptions on real chats before revising the design.
- Which real chats may the probe use? > "Both 1 and 2 I think": chats the user exports or pastes from personal accounts, and this Mac's Claude Code sessions about Northstar. Results stay off the repo.

After labelling the knowledge items from the first probe, the user wrote (2026-10-10, verbatim):

> "I noticed that, even is my own idea, sometimes it is just I personal preference like U22, but it doesn't worth remembering it, I think there is also a value threshold? Something you might want to consider a level deeper for me."

> "Also what I am saying dont keep is for the potential "northstar memory system", not saying I dont want this to be remember for my project."

> "I kind of feel like this is a bad example as this chat is mostly I talked about how to design "northstar", so they are all technical but only about the project, and it doesn't have much value once it goes outside this project, and thus I am not even sure if they should be in "northstar", I guess not? That why I put a lot to be "dont keep" but I am not sure now."

> On the knowledge-map prototype: "Why giving me all the G#? Very confusing." "I am not sure how to read through them, I dont feel like it helps me very much with my logic flow. I need a way better structure, I think this is where you need to research on: what format is best for human, and what kind of job needs to perform to make them happen? I guess not just simply paste the original words. You think deeper for me."

In the same review, the user's blind choices between replies preferred a reply without memory over one given strongly linked knowledge in 2 of 5 pairs, and a general profile over linked knowledge in 1 (see the probe record kept outside the repo).

On 2026-10-14, after a second review (four candidate formats for the human view, all rated poorly; four reply pairs with a revised way of giving memory to the AI), the user wrote (verbatim):

> On the formats: "Still they all read like an answer from Claude/ChatGPT or whatever, not a real helpful format."

> On memory in replies: "I can potentially see a problem, so don't make northstar stop the AI from its own creativity, otherwise I am stuck with the old knowledge, the knowledge should be added at the end or in parallel then synthesis with fresh answer. I will leave it to you to explore."

> On four design choices (project layer, when a project principle becomes personal, where working-style preferences live, whether memory use is shown in chat): "For these quick questions, maybe let them be configurable, honestly I am kind of not sure about the effects." Their picks, as starting defaults: leave project-only knowledge to each product's own memory or project files; a principle becomes personal only once it appears in a second context; Northstar keeps a small working-style profile; showing memory use in chat: unsure.

> "Again right now you are helping to explore the design, the design is not settled yet, let me know if you want this to be a new session so start fresh"

On 2026-10-15, co-designing the human view before anything was generated, the user answered (verbatim; picks from offered options in quotes, free text as written):
- When would you actually open your knowledge view? > Picks: "Preparing for something", "Checking a decision", "Rarely, if chat does it". Free text: "Also I was imagining like an index of a book, so I can quickly capture some ideas. I won't really go into details and the details shouldn't be fixed like reading a textbook for my exam, because usually it is open world problems like my interview."
- Outside AI chats, which formats have you actually gone back to and found helpful? > Picks: "Diagrams or mind maps", "Tables or cheat sheets", "My own short notes". Free text: "Images are usually helpful, but like pictures, but like my actual work. I think the key is it is my actual work, ones something I got my hands on it is helpful."
- When you open it, what should you see first? > "The big picture"
- Where would you open it? > "I am not sure, maybe most likely an AI assistant helping."

Asked to confirm this reading (a big-picture index glanced at before an interview or when checking a decision, not read through; details not fixed text but expanded by an AI assistant for the open-ended problem at hand; entries pointing to their actual work; the AI bringing knowledge up in chat most of the time, so the index is opened rarely; replacing "reads like a textbook"), the user answered (verbatim):

> "Yes that is my idea, but maybe not the best, you explore for me"

> Which sketch is closest to the "index" you imagined (contents page, back-of-book index, map)? "Map"

> What counts as "your actual work" that entries should point to? "Anything I got my hands on, not just something I glance or read through"

Later the same day the user reacted to two rounds of index sketches. These answers were recorded in `EXPLORATION.md` §3 at the time and added here on 2026-10-24; quotes are verbatim, picks from offered options in quotes.

Where their actual work lives:
- Code: "GitHub (personal)", "Work Git server", "Local folders only", "Mostly inside AI tools".
- Notes and documents: "I dont really have too many notes."
- Diagrams and images: "Inside docs or repos".
- Work material: "Personal only for now".

Round 1, three map shapes (a topic map, a position map, a work map):
- Which direction works? "None I guess, all looks unhelpful".
- Why unhelpful? Picked "The shape", not the content.
- Expansions: "Partly, like reference with session path doesn't really help, it is just a path string to me".
- What would make a work reference useful? "Show what I did there", "One line on what it shows".
- Links the AI spots in their work: "Only if I confirm".
- Where the view lives: "You decide".

Round 2, work first (A, inside an assistant reply; B, a work wall):
- Pick: > "A · inside the assistant | I would assume the work wall will be fixed? I would like to interact with AI and learn, if the work wall is also dynamic then I would probably work on both, still towards assistant as I can ask questions.  (ONLY if the assistant you meant like ChatGPT or Claude, not a self created one)"
- Compared with the maps: "Much closer". Why: "Seeing my real work brings it back", "One line per item is enough".
- The source tags: "Too busy". The left-out list: right. Where: "In the assistant, when I ask".
- Their words: > "I am not sure which part are you asking me to review: is this the memory part? Or the human version of memory?  If it is the later one then looks fine, if it is the first one it looks kind of off: human version should have its own structure and only for revisiting, not for generating new ideas.  I would still love to have a data/knowledge structure for human side, and a nice overall display format just like the maps in the last version, but better and smarter, this requires researchs."
- What the assistant should give back for a problem: "I am not sure yet".
- Which parts the next overall display should combine: "Big picture first", "Connect/conflict lines", "Grouped by topic". Not picked: "Work as the entries".

The same day, after blind-ranking five kinds of reply on six first messages (probe round 4: no memory, memory added at the end, memory merged in parallel, memory in the prompt, one-pass fresh-first), the user wrote (verbatim):

> On the interview set: "Really hard to tell which one is the best, all looks similar (tho I can tell which one doesn't have my knowledge)."

> On the framework-choice set: "I dont like any of them either, sounds very close world, not an answer I expected from powerful model like Opus or Astra, which I used mainly." On the side-project set: "Same issue, too amateur."

> On the design-doc review set: "Some answers sound like it is missing context, this is new conversation, then it shouldn't assume anything."

> Overall: "First of course, it is the answer itself. Secondly, dont assume context for new conversations. The key is to provide memory for the AI agents/LLM, not to alter the behaviours."

Asked what these notes mean (picks from offered options, verbatim):
- How did you order the replies below your top pick? > "Depends on the set"
- "Don't assume context for new conversations": which do you mean? > "No unstated facts" (don't presume things I didn't say) and "Don't cross projects" (don't carry a lesson from one project into another). Not picked: "Don't talk about my past"; "New chats start blank".
- "Provide memory for the AI, not alter the behaviours": which is closest? > "Plain context, no rules" (give the AI the memory with no instructions on how to use it; the AI decides), "No visible memory talk" (memory may change what the reply says, but no labelled sections and no talk about me) and "Facts, not judgment" (memory adds what the AI doesn't know; it doesn't push my past views or change what the AI covers). Not picked: "Never touch the reply".
- What should the next test compare against? > "My real apps" (the model as I normally use it, with its own memory, project files and web, compared with the same setup plus Northstar)

Later the same day, on in-session focus, the user wrote (verbatim):

> "Also one thing I didnt see from the probe: one capability is to keep the AI focus, it should talk about the stuff related to my goal, and capable to guide me through.
>
> For 2 example I experienced in the pass:
>
> 1. I am preparing for an interviewing for agent system design, AI gave me questions and critiques, then I keep asking questions about my own ideas, then the AI just keep on giving me questions on AI agent design, instead of really have a big picture that this is for interviews, it should help me with succeeding in interviews instead of just keep asking me questions (which helps in a way but not directly)
> 2. For the my-website project here in another project, I keep asking my minor ideas to help it improve, the first design draft was already good. So it should stop somewhere and ask me to open a new session instead of the long session which follows my idea but in a sense the art looks worse now.
>
> Hope you understand the deep thinking behind my words, and let me know the next step."

Asked to confirm a reading (focus is a separate job from memory: it watches the course of the conversation against the goal, speaks up rarely, and never rewrites answers), the user answered "Yes". They allowed the focus probe to use all their my-website Claude Code sessions. Asked how firmly it should speak up, they asked "What do you mean speak up". The marking page that followed explains it with an example.

Then the user framed the system as jobs (verbatim):

> "So I guess 2 different jobs like you mentioned:
>
> 1. Focus, a side job
> 2. Memory, add context
> 3. (Behind the scene) Maintain both AI and human memory structure"

Later the same day, the user marked their website session on the focus marking page; the per-message marks stay in the probe workspace. They marked 8 of 20 messages: six "suggest a fresh session" and two "step back to the goal", with none "say it is getting worse". Their answers (verbatim):
- What was this session for? > "For a design demo, then it will need to consider whether the current session is needed to continue or not, based on human's feedback. I am not sure if there is a systematic way to determine this."
- Which pictured message shows the best version of the site? > "After message 14" (mid-session, not the first draft).
- When it speaks up, how firm should it be? > "Not sure: make it a setting."
- Notes on rows: "Continue? It is just hitting the session limit." (two early pauses); "Continue as it should be a new session from previous chat" (two messages after a "fresh" mark); "Only if it is applicable" (on one "fresh" mark).

Asked which raw session data to copy into the probe workspace (website and Northstar sessions, Codex sessions, Claude scratch workspaces), the user answered (verbatim): "Anything you think is helpful". Asked whether to run the focus replay as planned (staged; about 1.1M tokens first, stopping to ask past about 4M), they picked "Yes, staged (Recommended)". After stage 1 failed its bar (EXPLORATION §2), they approved the proposed follow-up (verbatim): "Yes, run the graded-score rerun of the screenshot watcher as proposed in focus-replay-plan.md."

After the graded rerun also failed, the user marked, for each of their marks, what told them it was time (one-tap options, the full list kept in the probe workspace). They picked "a side topic, not the site design" for the three earlier marks, and "the chat had got long or cluttered" for four of the five later ones, with "the design was as good as it would get" (three marks) and "a phase was done" (one). Their words (verbatim):
- Why the version after message 14 was best: > "Just a feeling. Again I am not artist and you didnt really show me the full site, just some screenshots."
- Anything else: > "I guess some watcher can tell by session being too long and knowing the goal."
- Could a watcher have known these moments without knowing you? > "Some of each"

Asked which session to hold out for the next focus test, the user answered (verbatim): "Use the long Northstar exploration session (15 messages, Oct 8-15) as the held-out test. Build the marking page for it, then run the size-aware watcher (about 0.9M tokens) once I've marked it."

On 2026-10-16 the user marked that session (per-message marks kept in the probe workspace). They marked 7 of 16 messages "suggest a fresh session", one of them qualified ("Continue or, depends on how you think"), and one also "step back to the goal" and "it is getting worse"; best version: none. Their notes on marks include "Bad performances and answers from previous rounds", "Research maybe" and "Looks like you start breaking things now". Their answers (verbatim):
- What was this session for? > "For explore/design"
- Anything else? > "Just like this round is for probe the concept, do you need to start research now? Are you drifting? Including the main thread?"

On 2026-10-23, answering in a side session (relayed with their words quoted), the user agreed to one last test and then consolidation. Their words (verbatim): "Yes. Tell the focus replay session to run the held-out test exactly as planned (no Fable arm), then close the probe phase with a handoff for the revised design, to be written on Opus 5.5 at xhigh."

On 2026-10-24 the user answered the revised design's review page (`docs/design/revision-2026-10-23/review.html`). Picks from offered options and notes, verbatim:
- Q1, how focus decides when to speak: "(b) Lighter plus its own quality check at those moments". Note: > "I am kind of not sure, what you described just sounded like an alarm system, doesnt have any value from AI side, especially you said "from my input"."
- Note on focus: > "It feels kind of weak if it is always shown to me and I need to decide whether going to AI or not, I hope some intelligence can help.
>
> Also it looks like an alarm/reminder if you just open on the side, not useful for AI tools like Claude."
- Q2, does the overview only revisit: "Not sure yet".
- Q3, three readings of their words: "Not quite (see my note)". Note: > "First 2 I am not sure, it is your design problem, I am not sure which is the better approach.
>
> 3rd one is correct."
- Q4, where the first prototype runs: "(a) This Mac first, Windows right after".
- Q5, the design as a whole: "Approve with the changes in my notes". Note: > "I am also hoping you find researches and papers, to back up your design."
- Note on maintenance: > "I still dont see an architecture of the memory system yet: at first I was hoping I could have an architecture/system built for each AI and human, with probes maybe it changed. But shouldnt there is something like OpenAI dreaming architecture that is here?"

Later on 2026-10-24 the user answered revision 2 on the same page. Picks and notes, verbatim:
- Q6, does the new focus match what you meant: "Yes". Note: > "Ideally I want the AI to be with claude/chatgpt, or the platform I am using like any customized harness etc. It should be generalized and instead of seperated, unless you tell me it has to. I am thinking from a product experience perspective."
- Q7, does the architecture answer your note: "No (see my note)". Note: > "When I said dreaming, i am talking about the ChatGPT dreaming memory system, not literally sleeping dreaming."
- Q8, go ahead (research and sketch the overview, then the Claude Code prototype on this Mac): "Yes, with the changes in my notes".

On 2026-10-25 the user answered revision 3.1 on the same page. Picks and notes, verbatim:
- Q9, is this what you meant by ChatGPT's Dreaming memory system: "Partly (see my note)". Note:
  > "Dreaming I meant:https://openai.com/index/chatgpt-memory-dreaming/
  >
  > And I didnt mean literally: I was just referring to my northstar in a sense like this, it have memory structures (AI and human), and it helps with focus and memory, also it still works with existing AI like ChatGPT and Claude, it is not on its own. (Better commercial this way and able to embrace the powerful world class AI)"
- Q10, how should Northstar's hidden sub-tasks reach your AI (through the API on the same models, on your Claude and ChatGPT plans, or decide after a test): no pick. Note: > "I have no idea, you design, based on what I told you."
- Q11, may Claude and ChatGPT check each other's work: "Yes, they may check each other".
- Q12, what may the overview sketches use: "My website work, plus chats I add to the probe inbox". Note: > "I can also give you a few chat example I had."
- Q13, when should the phone come (after the four first connectors, or second as on 2026-10-09): "Not sure yet".

On 2026-10-27 the user took the overview test of the sketch round (two sketches built from their website work and three ChatGPT chats they sent on 2026-10-25; their lookup answers stay in the probe workspace). Before starting they asked: > "you want to test me on how much I remember the old chats?" and > "so it gives me a timer to find the info I need/it quiz?" Their answers on the design, verbatim:
- Which form would you rather use (sketch A, the outline; sketch B, the map; either; neither): "Neither". Why: > "Leaning towards B but still not very helpful. I asked for a deep research on what is the best form, article/papers/published etc,."
- "Ask about this for my problem": "I'd use it".
- Should the overview only help you revisit, or also expand an idea for a problem: "Not sure".
- Anything the overview got wrong or missed: > "This is what I think right?"

On 2026-10-28, after the deep research on the overview's form (notes 26, 26a–26d; findings page), the user was asked which should be the overview's first view: a smarter map (fewer entries in their own words, their work on each, lines around the idea in focus, a stable layout) or a text hub with the map second. Their pick: "Smarter map first".

Later on 2026-10-28 the user looked at the look-and-react round: one overview with the smarter map, "where you left off" and ask, plus a text version, built from the same three chats and their website work, with no timer. The page and their full notes stay in the probe workspace. When it opened they asked: > "wait what am I doing exactly". Their notes, verbatim:
- What works: "-" (left empty).
- What doesn't: > "I dont know I feel like it is just again and again you asked me to repeatly look at something very unhelpful, it seems like you showed me this already"
- Which way in did you use first: "Where you left off". The page's own log shows the map first, and no "where you left off" card opened.

Right after that round, the user named two gaps (verbatim):

> "So there's two real gaps I see. First, not sure if you have decided and researched on the architecture for both AI knowledge and human knowledge. So I was assuming there's some algorithms and some data structure behind the scene for retrieval and storage. And also expansions and consolidation, etc. Those already in your notes? Second thing is that what is missing is the view of this human whether it's just blend into ChatGPT or Claude, it uses some sort of UI the maps you give me, or some mind map, that you do the research on those as well. So these are the gaps I kind of see."

The original brief still applies: people learn continuously through AI conversations, research, work, reading and their own thinking, but this knowledge accumulates as disconnected fragments instead of a coherent, evolving understanding. Its foundations are:
1. the structure of knowledge and memory;
2. update and evolution without fragment pile-up or loss of history;
3. human use and AI use, which need not share one representation;
4. integration with ChatGPT, Claude and Codex.

The end state is a working system that has been built and tested.

## 2. The user's answers to the design questions (2026-10-07)

| Question | Answer |
|---|---|
| AI-side priority: in-session drift in one long chat, or continuity across chats? | **Both equally** |
| First AI surfaces | **Claude.ai and ChatGPT (web) first**, then Claude Code / Claude Desktop and ChatGPT Desktop |
| "Structural memory of what to learn": what was learned, or what to learn next? | **Both** |
| May the AI build and reorganize the structure automatically, with the user correcting it? | **Yes** |
| Human-side interface | **No preference: pick the best solution** |

**Answers of 2026-10-08.** These supersede the table above where they conflict.

| Question | Answer |
|---|---|
| Surfaces, if the web (claude.ai / chatgpt.com) is hard | **The desktop apps are fine.** Ideally **chat and code for both products**: Claude Desktop chat and Claude Code; ChatGPT Desktop chat and Codex. A web browser extension is **not required**. |
| Accounts | **Personal accounts mainly**; enterprise support would be welcome later |
| Where data lives | **Local now, cloud later.** The architecture must support both |
| Estimating "how well you know it" | **No.** That is a usage detail, not the goal. The human side must **help the person understand and remember their knowledge, as a textbook does** |
| Product coupling | **Product-agnostic.** The system serves **any AI agent or LLM**. ChatGPT, Claude and others reach it through **connectors** |

**Answers of 2026-10-09.** These supersede the tables above where they conflict. The user's verbatim words are in §1.

| Topic | Answer |
|---|---|
| Platforms | **Not Mac-only.** Should work on Windows and Mac (a strong preference, not a non-negotiable); assess platform dependencies and state limitations and tradeoffs. **Order for the prototype: Windows first, iOS second, Mac last**, with the ranking "pretty close" |
| Devices | **Many machines, and potentially phones**, sharing one memory |
| Connectors | No mandate for MCP or against product-specific connectors. Choose by **actual effectiveness** for capture, in-session focus and cross-session continuity |
| Knowledge organization | New material connects to relevant existing knowledge. The structure evolves **in both directions**: sections extend, subdivide into subsections or branches, and related branches merge or are summarized at a broader level. The design must explain how it decides where material belongs and when to subdivide or consolidate |
| Personal relevance | The memory **centres on the user's evolving ideas, viewpoints, reasoning, interests, and the questions or problems they want to explore**, including understanding developed with AI. **Personal relevance** decides what is organized and what counts as a gap, not subjective vs objective. Generic, readily searchable information does not become organized knowledge or a learning gap merely because a term appeared. Objective information matters when it directly supports the user's thinking or problems. Not a generic encyclopedia or glossary |
| Evaluation | **Baseline first:** measure without Northstar, then with it, on comparable scenarios, with improvement defined. A **manageable initial benchmark** covering AI assistance and the usefulness of the human-facing organization; meaningful measurements, not impressions; less rigor than a SWE-style benchmark. **Short one-off sessions with the user** before and after are fine. Scenarios are built from the **user's real topics** |
| Deliverable | A revised proposal, a concise explanation of the major changes, and unresolved questions and tradeoffs. Stays at the proposal and evaluation-plan stage; the approval process is unchanged |

**Answers of 2026-10-10.** These supersede everything above where they conflict. The user's verbatim words are in §1. The user asks that these be treated as direction to reason about, not as hard specifications.

| Topic | Answer |
|---|---|
| Unit of memory | **The user's own knowledge**: their ideas, conclusions, principles, approaches and positions, **validated through discussion or research with AI**, each with its reasoning (why), where it applies (context or scope), how they got there (the discussions and research behind it), and its connections, including conflicts across contexts (e.g. "real development" vs "interviews"). Ideas not yet validated may be kept as still forming. Not a collection of AI explanations |
| What becomes memory | An AI answer does not become memory just because the user asked a question. Memory starts when the user's own statement, follow-up, agreement or disagreement shows where their thinking is going. The user's opinions are recorded as theirs; what AIs taught becomes knowledge when it is correct (validated) and adopted |
| AI-said content | **Adopted AI teaching is first-class and attributed**: what the user agreed with, built on or used. Other AI answers are kept only in a **private, searchable raw archive**, never shown or injected on their own |
| The human view | **Short**: a map of the user's knowledge that connects the dots, with depth on click. AI explanations are sources one click away, not Book content. The earlier long, explanatory textbook is too long |
| Context for the AI | Inject **relevant context based on the current conversation**, not general context. The user's views and knowledge enter a chat **only when very strongly linked**, not when merely linked or mentioned |
| Rules | Prefer **dynamic** behaviour over hard-coded thresholds where possible |
| Order of work | **Probe first, then revise**: test the riskiest assumptions on real chats (the user's exported or pasted chats and this Mac's Northstar Claude Code sessions), then revise the design. Results and personal data stay off the repo |
| Open decisions | Every recommendation in ARCHITECTURE §14 accepted, except DQ-15 (only when very strongly linked) and DQ-17 (to be revised under the points above) |
| Value threshold | Being the user's own idea is not enough: some of it (for example a passing preference) is not worth remembering. A **value threshold** is needed, worked out "a level deeper" |
| Project vs personal | "Don't keep" in the probe meant **not for the personal Northstar memory**, not "forget it for the project". Project-only knowledge has little value outside its project; whether it belongs in Northstar is open (the user leans no) |
| Human view format | The knowledge-map prototype did not help the user follow their logic; internal IDs were confusing. A **much better structure** is needed, based on research into which format works best for people and which processing jobs produce it, **not just pasting the original words**. (2026-10-14) Four research-based text formats were also rejected: they "read like an answer from Claude/ChatGPT", not a real helpful format |
| Memory in AI replies (2026-10-14) | Northstar must **not stop the AI's own creativity** or leave the user "stuck with the old knowledge". Direction to explore: the fresh answer comes first, and knowledge is **added at the end or in parallel, then synthesized** with the fresh answer |
| Configurable choices (2026-10-14) | Uncertain design choices become **settings with defaults**, because the user is unsure of their effects |
| Status (2026-10-14) | **The design is being explored, not settled.** ARCHITECTURE.md and the revision documents are earlier proposals, not the current design |

**Answers of 2026-10-15.** These supersede everything above where they conflict. The user's verbatim words are in §1. The user confirmed the direction and asked us to explore the best form of it ("maybe not the best, you explore for me").

| Topic | Answer |
|---|---|
| Role of the human view | **A big-picture index of the user's ideas, not a textbook.** The user glances at it to recall ideas quickly; they do not read through it |
| When it is opened | **Preparing for something** (an interview, a meeting, writing) and **checking a decision**. When the AI side brings knowledge up in chat at the right moment, the user expects to open the index **rarely** |
| Depth | **Not fixed text.** The user's problems are open-world (for example an interview), so details are not written in advance like a textbook for an exam. An **AI assistant expands an entry for the problem at hand** |
| Shape | Closest to a **map**: the main topics, with lines where ideas connect or conflict. **The big picture comes first** |
| What entries point to | **The user's actual work: "anything I got my hands on"**, not only what they glanced at or read. Images of their actual work, diagrams or mind maps, tables or cheat sheets and their own short notes are the formats they have found helpful |
| Where it is opened | Not settled; "most likely an AI assistant helping" |
| Memory in AI replies (after probe round 4) | **"The key is to provide memory for the AI agents/LLM, not to alter the behaviours."** Memory reaches the AI as **plain context with no usage rules**; the AI decides how to use it. Memory may change **what** a reply says, but the reply has **no visible memory talk**: no labelled memory sections and no talk about the user. Memory adds **facts the AI lacks, not judgment**: it does not push the user's past views or change what the AI covers. **First comes the answer itself** |
| Context in new chats | **Don't presume facts the user didn't state**, and **don't carry a lesson from one project into another**. New chats do **not** start blank: cross-session continuity (§3) is unchanged |
| The 2026-10-14 "fresh answer first" direction | **Refined, not replaced.** The user did not choose "never touch the reply", so a second pass is not ruled out, but any form must meet the two rows above |
| Showing memory use in chat (undecided on 2026-10-14) | **No memory talk inside the reply** by default. The user found the labelled "From your earlier thinking" part useful only "sometimes". Whether a separate note outside the reply helps is untested; it stays a setting |
| Baseline for evaluation | **The user's real apps as they normally use them** (their own memory, project files and web), compared with the same setup plus Northstar |
| How the system divides into jobs (the user's own framing, §1) | **Three jobs:** (1) **Focus**, "a side job" in the conversation; (2) **Memory**, which adds context; (3) **behind the scenes, maintaining both the AI and the human memory structure**. Open questions: does "side job" mean it runs beside the chat, or ranks below memory (§3.3 weighs focus and continuity equally)? Who serves the human index when the user glances at it or asks for depth: memory, or a separate job? Analysis: `research/round4/three-jobs-analysis.md` |
| In-session focus (confirmed by the user, after the two examples in §1) | **Focus is a separate job from memory.** Northstar holds the **goal above the current activity**: "succeed in the interview", not "keep practising agent-design questions". It judges **whether the work is still getting better**, and **speaks up rarely**, to step back to the goal, to flag that changes are making things worse, or to suggest a **fresh session that carries the goal and the best version so far**. It never rewrites answers, so "provide memory, not alter the behaviours" still holds for answers. How firmly it speaks up is not yet decided |
| Focus: firmness and fresh sessions (marking page, later on 2026-10-15) | **How firmly focus speaks up is a setting.** Whether a session should continue or start fresh is judged **from the human's feedback** in the session; the user is **not sure a systematic way exists**. On their website session they wanted a fresh session suggested at six points, and picked a **mid-session version as the best**, not the first draft |
| Human view, sketch rounds (later on 2026-10-15; recorded here 2026-10-24) | Three map shapes were rejected **for their shape**. The work-first sketch was "much closer": **seeing their real work brings it back, one line per item is enough**. A work reference should **show what they did there, with one line on what it shows**; path strings do not help. Links the AI spots are shown **only once the user confirms** them. The human version **"should have its own structure and only for revisiting, not for generating new ideas"**. They still want **a data/knowledge structure for the human side and a better, smarter overall display**: big picture first, grouped by topic, connect and conflict lines, which "requires researchs". It lives **"in the assistant, when I ask"**: ChatGPT or Claude, not a separate app. Personal material only for now |

**Answers of 2026-10-24** (the revised design's review page; verbatim in §1). These supersede everything above where they conflict.

| Topic | Answer |
|---|---|
| The revised design of 2026-10-23 | **Approved with changes.** The changes are the notes in the rows below |
| Focus | Pick: **the lighter role plus its own quality check** at the moments it may speak. The user is "kind of not sure". Notes shown beside the chat read as **"an alarm system" with no value from the AI side**; judging "worse" only from the user's own input is too little; the user does not want to be the one deciding whether to go back to the AI: **"I hope some intelligence can help"**; a note opened on the side is "not useful for AI tools like Claude". Reading for the design, to confirm with the user: focus should bring the system's own intelligence and deliver its value through the AI in the conversation, not only as notes on the side |
| Human view depth | **Not sure yet** whether the overview only revisits or also expands an idea for a problem. Open; both can be tried in the sketch round |
| "Facts, not judgment" | **Confirmed:** decisions, results, conclusions and what things are go to the AI when strongly linked; the user's views and principles go only when the AI asks for them |
| What "side job" means; who serves the human overview | **Left to the design** ("it is your design problem") |
| First prototype platform | **This Mac first, Windows right after.** This supersedes the 2026-10-09 order for the first prototype |
| Architecture | The user still wants to **see an architecture of the memory system for the AI and for the human**, as they hoped at the start (§1, 2026-10-07), and asks whether something **like OpenAI's "dreaming"** belongs here. To research |
| Evidence | The design should be **backed by research and papers** |

**Answers of 2026-10-24, round 2** (revision 2 of the design; verbatim in §1). These supersede everything above where they conflict.

| Topic | Answer |
|---|---|
| Focus | **Confirmed:** at a few moments it works out what the goal still needs, checks the work, and speaks through the AI, which answers first, offers in two sentences, and acts only on a yes |
| Where Northstar's intelligence runs | **On the AI the user is already using**: Claude, ChatGPT, or "any customized harness". It "should be generalized and instead of seperated, unless you tell me it has to", from "a product experience perspective". Northstar should not feel like a separate AI. Where separation is needed, the design must say so and why |
| "Dreaming" | The user means **ChatGPT's Dreaming memory system**, the product feature, **not sleep** as a metaphor. The architecture should be shown in those terms |
| Next steps | **Approved** with the two changes above: first research and sketch the overview, then build the Claude Code prototype on this Mac |

**Answers of 2026-10-25, round 3** (revision 3.1 of the design; verbatim in §1). These supersede everything above where they conflict.

| Topic | Answer |
|---|---|
| What "like OpenAI's dreaming" meant | **Not a literal copy**, neither of sleep nor of ChatGPT's mechanism. ChatGPT's Dreaming memory system (openai.com/index/chatgpt-memory-dreaming) is a reference for what Northstar is "in a sense like this": it **has memory structures (AI and human)**, it **helps with focus and memory**, and it **"still works with existing AI like ChatGPT and Claude, it is not on its own"**. The user's reason: "Better commercial this way and able to embrace the powerful world class AI" |
| How Northstar's hidden model calls reach the user's AI | **Left to the design:** "you design, based on what I told you" |
| Checks across vendors | **Allowed:** Claude and ChatGPT may check each other's work |
| Material for the overview sketches | The user's **website work, plus chats the user adds to the probe inbox**; the user offered "a few chat example" |
| The phone in the platform order | **Not sure yet** |

**Answers of 2026-10-27** (the overview sketch round; verbatim in §1). These supersede everything above where they conflict.

| Topic | Answer |
|---|---|
| The overview's form | **Neither sketch** (a topic outline; a stable topic map) is good enough: "Leaning towards B but still not very helpful" |
| How the form is chosen | The user expects **deep research on the best form**, drawn from "article/papers/published" sources, before a form is settled |
| "Ask about this" from the overview | "I'd use it" |
| Revisit only, or also expand | Still **not sure** |

**Answer of 2026-10-28** (after the deep research; verbatim in §1).

| Topic | Answer |
|---|---|
| The overview's first view | **A smarter map**: the user's own words, a few entries per topic, their work on each, lines around the idea in focus, a stable layout. "Where you left off" and "ask" are the other two ways in (research note 26) |

**Answers of 2026-10-28, later** (the look-and-react round; verbatim in §1). These supersede everything above where they conflict.

| Topic | Answer |
|---|---|
| The look-and-react round (the smarter map, "where you left off", ask) | **Not helpful.** Nothing was marked as working. The user feels asked "again and again" to look at "something very unhelpful", and: "it seems like you showed me this already" |
| Which way in came first | "Where you left off", by the user's pick; the page logged the map first |
| Two gaps the user sees | (1) **The architecture for both AI and human knowledge:** the algorithms and data structures behind storage and retrieval, expansion and consolidation; the user asks whether these are already in the notes. (2) **How the human view appears:** blended into ChatGPT or Claude, a UI such as the maps, or a mind map, with research on these too |

## 3. What we are building

A **memory system**: an architected product, not a practice. It has these parts.

1. **A shared knowledge core.** It captures conversations **on both sides**: what the user said and what the AI said, told or taught. Over time it can take in other sources such as reading and work. It keeps knowledge structured, attributed (who said it, and where it came from) and evolving, without destroying history.
2. **The human architecture: a structural memory.** A navigable structure the AI maintains, covering:
   - **what has been learned**, from the user's own thinking and from what AIs taught;
   - **what to learn**: goals, gaps, open questions, next steps.

   **It reads like a textbook.** The AI organizes the knowledge and explains it so the person **understands and remembers** it when they read. Every explanation stays traceable to its sources: who said it, and in which conversation. It is not a quiz or a mastery score.

   The user browses it and can correct it. Any human routine is an optional way of using it, never a requirement.

   **(2026-10-09)** It centres on the user's evolving ideas, viewpoints, reasoning, interests and the questions or problems they want to explore, including understanding developed with AI. **Personal relevance** decides what is organized and what counts as a gap; it is not a generic encyclopedia or glossary. The structure evolves in both directions: extend, subdivide, merge, and summarize at a broader level (§2, 2026-10-09).

   **(2026-10-10)** Its unit is **the user's own knowledge**: ideas and conclusions validated through discussion or research with AI, each with why, where it applies, how it was reached and how it connects. The view is **short**, a map that connects the dots with depth on click, not a long explanatory textbook; AI explanations are one-click sources (§2, 2026-10-10).

   **(2026-10-15, confirmed by the user)** This replaces "it reads like a textbook" above. The human view is a **big-picture index of the user's ideas, closest to a map**: topics, with lines where ideas connect or conflict. The user glances at it when **preparing for something or checking a decision**, and does not read through it. **Depth is not fixed text**, because the user's problems are open-world: an **AI assistant expands an entry for the problem at hand**. Entries point to **the user's actual work, anything they got their hands on**. When the AI side brings knowledge up in chat at the right moment, the index is opened rarely. The user asked us to explore the best form of this direction (§2, 2026-10-15).

   **(Sketch rounds of 2026-10-15, recorded 2026-10-24)** The human side has **its own knowledge structure** and a better, smarter overall display: big picture first, grouped by topic, with connect and conflict lines. The user's real work, shown as what they did with one line each, brings ideas back. It is **for revisiting, not for generating new ideas**, and lives **in the assistant (ChatGPT or Claude) when the user asks**. Whether it also expands an idea for a problem is open (§2, 2026-10-24).
3. **The AI architecture: a memory system for AI assistants** that goes beyond memory files. It is **product-agnostic**: it serves any AI agent or LLM, and each product (Claude, ChatGPT, Codex, others) reaches it through a **connector**. It serves the following, **equally weighted**:
   - **In-session focus.** In a long chat, the AI's answers keep serving the user's goal. They don't drift away from what was already established, whether the user or the AI established it.
   - **Cross-session continuity.** A new chat starts with the relevant goals, knowledge and conclusions from earlier work, without the user re-explaining.

   **(2026-10-15, confirmed by the user)** In-session focus means more than not forgetting. In the user's examples the AI forgot nothing: it followed each latest message and lost the goal the session existed for. Northstar holds that goal above the current activity, judges whether the work is still improving, and speaks up rarely: to step back to the goal, to flag that changes are making things worse, or to suggest a fresh session that carries the goal and the best version so far. This is a separate job from supplying memory, and it never rewrites answers (§2, 2026-10-15).

   **(2026-10-15)** Northstar **provides memory to the AI; it does not alter the AI's behaviour.** Memory goes in as plain context without usage rules, adds facts the AI lacks rather than judgment, and leaves no visible memory talk in the reply. In a new chat it presumes no facts the user didn't state and carries no lesson from one project into another (§2, 2026-10-15).
4. **AI-managed maintenance that holds up against its own attention loss.** The AI does all capture, structuring, consolidation and reorganization. The maintainer can itself lose focus, so the architecture must make maintenance reliable and checkable. It must not depend on one agent staying attentive.

## 4. Non-negotiables (the WHAT)

Agents may not change any of these. If evidence shows one is infeasible or risky, **flag it explicitly as a risk for the user**. Do not silently replace it with something else.

1. **It is a system.** The product is software architecture. It must deliver value without requiring the user to do regular review sessions, journaling or rituals.
2. **AI-said knowledge is first-class.** What the AI explained or taught is part of the memory, attributed as AI-said. Memory is not limited to the user's own statements or commitments. **(2026-10-10, confirmed by the user)** First-class means: what AIs taught that the user adopted (agreed with, built on or used) is first-class and attributed. Other AI answers are kept only in a private, searchable raw archive and are not memory on their own.
3. **The AI manages it.** Automatic capture, structuring and reorganization are the default. Human correction is available, never required.
4. **Two architectures, one human-facing and one AI-facing**, over a shared core. Their representations may differ.
5. **The AI side addresses both in-session drift and cross-session continuity.**
6. **Product-agnostic core, with connectors.** The first connectors are for Claude and ChatGPT, **both chat and code**: Claude Desktop chat, Claude Code, ChatGPT Desktop chat and Codex. The claude.ai and chatgpt.com web apps are welcome but optional; a ToS-grey browser extension is not required. Deployment: local now, cloud supported later. Personal accounts first, enterprise later. **(2026-10-09)** Not Mac-only: Windows and Mac are a strong preference; prototype order Windows, then iOS, then Mac (close ranking); many machines and potentially phones share one memory (§2). **(2026-10-24)** The first prototype runs on this Mac first, with Windows right after (§2).
7. **The maintainer is robust:** maintenance must stay correct even when an individual agent loses focus.
8. **We build and evaluate a working prototype.**

## 5. Freedom (the HOW)

Agents decide architecture, storage, hosting, models, knowledge representation, algorithms, interfaces and integration mechanisms. **Challenge the HOW freely. Never re-scope the WHAT.**

Earlier research findings are **constraints on the HOW**, not reasons to change the WHAT. They live in `docs/research/`. Examples:
- record attribution and provenance;
- supersede rather than overwrite;
- never summarize summaries;
- context rot;
- memory-induced sycophancy;
- prompt injection through stored memory.

## 6. What success looks like

- In a long chat on any connected product (first Claude and ChatGPT, chat and code), answers late in the conversation still serve the goal set early. The reduction in drift is **measured** against the same chat without the system.
- A new chat picks up the relevant goals, knowledge and prior conclusions without the user re-explaining. This is measured too.
- The user can open the human view and read their knowledge **like a textbook**: what they have learned from themselves and from AIs, organized and explained so it is easy to understand and remember. Each item shows its sources, and the view shows what they are working toward learning next.
- **(2026-10-15, replaces "like a textbook" in the point above)** Before an interview or a decision, the user glances at a big-picture index (a map) and quickly recalls their own ideas, including how they conflict across contexts. An AI assistant expands any entry for the problem at hand, and each entry reaches the user's actual work (§3.2).
- The system maintains itself without babysitting. Maintenance errors are bounded, detectable and correctable.
- **(2026-10-09)** Measurement is **baseline first**: the same scenarios, built from the user's real topics, are measured without Northstar and then with it, with improvement defined in advance. The initial benchmark is manageable and covers AI assistance and the usefulness of the human-facing organization; short one-off sessions with the user are allowed (§2).

## 7. Process rules (lessons from the rejected first design)

- **Order of work:** research → design → review → user approval → build.
- **Goal-fidelity check at every stage.** Each deliverable is compared with this file, and any drift is fixed before the work moves on.
- **What went wrong before.** The first design (v0.1/v0.2) replaced the goal with "a commitment ledger plus a weekly 20-minute ritual". The user rejected it. It is archived in `docs/archive/2026-10-07-rejected-design-v0.2/` for the record only. Do not build from it.
- **Reframing needs the user.** A proposal to reframe the goal goes to the user as a question. It is never adopted unilaterally.
