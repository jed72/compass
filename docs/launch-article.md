# My spec-driven dev tool works for me. That's the problem.

A few weeks ago I noticed which Compass command I was running most. Not the one
that frames a task, or the one that checks the work. It was the one that quietly
admits I got the framing wrong and re-does it. I built the tool to stop me
cutting corners, and the part I reach for most is the part that says "you called
this one wrong, start that bit again."

That's an odd thing to admit about something you built. It's also the most useful
thing I can tell you about it.

Here's the situation. I've been using Compass on my own work for a few weeks. It's
held up. I'm less annoyed than I was, the small changes stay small, and the scary
ones get the full treatment. But "it works for me" is about the lowest bar there
is. A tool whose whole job is to decide how much process a piece of work needs has,
so far, only ever been judged by one person's judgement: mine. That isn't tested.
It's just my own taste, automated. So I'm putting it out to find out whether the
idea survives other people.

## The quick version of what it does

In case you've not seen it. Most spec-driven setups run every change through the
same steps. What actually happens then is that people do the full ceremony on the
big, scary change and quietly skip it on the typo, because doing the whole routine
for a one-line fix is daft and everyone knows it. So the process ends up covering
the changes that were never going to hurt you, and getting skipped on some that
might.

Compass tries to fix that by splitting the rules in two. There are a few hard
guardrails that never move: tested before it lands, acceptance defined before it's
built, a human signs off on anything irreversible. And there's a set of softer
strategies, like TDD and BDD, which are the usual way of meeting those guardrails
but which you can step off, with a reason. Then it reads a few plain things about
the task, how risky it is, how big, whether it's greenfield or you're cutting into
something that already exists, and works out how much process to apply. A small
change gets a light path. A new subsystem gets the full set. The hard rules hold
either way.

I wrote that part up properly a little while back, if you want the longer version.
[The one-size-fits-all problem](https://medium.com/@James.edwards_75381/spec-driven-development-has-a-one-size-fits-all-problem-ff81378f69f0)

## Where I already know it's thin

Let me save you the trouble of finding the obvious holes, because I've found a few
of them already.

It's all been solo. I've never run it with a team, which is awkward, because half
the point of process is getting people to agree, and I've no idea how it behaves
when two people frame the same work differently. The whole thing leans on the
framing being roughly right, and as I said, the command I reach for most is the one
for when it isn't. I haven't pointed it at a big, messy, legacy codebase and
watched it struggle. And there's a fair chance that some of the things I think are
clever are just things that happen to suit the way I work.

None of that is false modesty. It's the actual state of it.

## Two things I'd genuinely like help with

First, use it on something small and throwaway, and tell me where it fights you.
Not just the obvious bugs, though do tell me those. I mean where the process it
picks feels wrong, or a guardrail gets in the way for no good reason, or you'd
plainly have done it differently. I learn far more from "this annoyed me, and
here's why" than from a star on the repo.

Second, tell me where to take it next. Right now it only plugs into Claude Code,
because that's what I use and it's all I've had time to build. The routing and the
checks are kept separate from any of that on purpose, so it could in principle run
elsewhere, but "could" is doing a lot of work in that sentence, and porting it
properly is real effort. So before I spend that time, I'd rather know what people
actually want: Cursor, Codex, Gemini, or just a plain command-line version with no
agent attached at all. If you've got a preference, that's the sort of thing that'll
decide what I do next.

Building the thing was the easy part, as it usually is. The bit I can't do on my
own is find out whether an adaptive take on this holds up once it meets work that
isn't mine and habits that aren't mine. That's the whole reason it's out this
early, rough edges and all. I'd rather hear where it falls over now than keep
polishing something that only ever made sense to one person.

If you want to try it, it's on GitHub at
[github.com/jed72/compass](https://github.com/jed72/compass). In Claude Code you
can add it as a plugin:

```
/plugin marketplace add jed72/compass
/plugin install compass@compass
```

Then start a task with `/compass:frame "..."`. There is nothing else to install -
the plugin carries what it needs - and the defaults work out of the box, so
there's nothing to set up first. It's early, so point it at a branch you don't mind
burning.
