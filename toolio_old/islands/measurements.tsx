import * as React from "react"
import { createRoot } from "react-dom/client"
import Terminal, { TypingAnimation } from "../components/ui/terminal"
import {
  COMMIT_CHURN,
  COMMIT_DATES,
  TEST_FUNCS,
  TEST_FUNCS_TOTAL,
  TEST_DATES,
  TEST_NAMES,
  SRC_LINES,
  SRC_DATES,
  SRC_NAMES,
  COMMIT_COUNT,
  FILE_COUNT,
  TEST_FILE_COUNT,
  TOTAL_LINES,
  CHURN_TOTAL,
  FIRST_COMMIT,
  LAST_COMMIT,
} from "./data"

const nf = (n: number) => n.toLocaleString("en-US")
const max = (a: number[]) => a.reduce((m, v) => (v > m ? v : m), 0)

type Key = "commits" | "tests" | "source"

const SETS: Record<Key, {
  tab: string
  matrix: number[]
  dates: string[]
  labels?: string[]
  unit: string
  unitPlural: string
  title: string
  caption: string
  stats: { label: string; value: string; sub: string }[]
}> = {
  commits: {
    tab: "commits",
    matrix: COMMIT_CHURN,
    dates: COMMIT_DATES,
    unit: "commit",
    unitPlural: "commits",
    title: "Every commit is a bar. The height is the lines it moved.",
    caption:
      "91 commits in order, one bar each. A tall bar is a commit that rewrote a lot - the day the pipeline, the plugin and the bridge were rewritten. A short one is a fix. The tallest is 30,636 lines.",
    stats: [
      { label: "Commits", value: nf(COMMIT_COUNT), sub: FIRST_COMMIT + " - " + LAST_COMMIT },
      { label: "Lines changed", value: nf(CHURN_TOTAL), sub: "added and deleted, all of them" },
      { label: "Busiest commit", value: nf(max(COMMIT_CHURN)), sub: "lines in a single commit" },
      { label: "Working days", value: "16", sub: "days that had a commit on them" },
    ],
  },
  tests: {
    tab: "test files",
    matrix: TEST_FUNCS,
    dates: TEST_DATES,
    labels: TEST_NAMES,
    unit: "test",
    unitPlural: "tests",
    title: "Every test file is a bar. The height is how many tests it holds.",
    caption:
      "164 files, 4,108 test functions, counted by reading the repository. The tall bars are the tool suites; the short ones are the helpers.",
    stats: [
      { label: "Test files", value: nf(TEST_FILE_COUNT), sub: "tracked, and counted" },
      { label: "Test functions", value: nf(TEST_FUNCS_TOTAL), sub: "collected by pytest" },
      { label: "Busiest suite", value: nf(max(TEST_FUNCS)), sub: "tests in one file" },
      { label: "Source files", value: nf(FILE_COUNT), sub: "tracked, and counted" },
    ],
  },
  source: {
    tab: "source files",
    matrix: SRC_LINES,
    dates: SRC_DATES,
    labels: SRC_NAMES,
    unit: "file",
    unitPlural: "files",
    title: "Every source file is a bar. The height is how long it is.",
    caption:
      "719 tracked text files, 208,447 lines, counted from git. The tall ones are the bridge, the plugin source and the context engine - the parts that have to stay correct.",
    stats: [
      { label: "Source files", value: nf(FILE_COUNT), sub: "tracked, and counted" },
      { label: "Lines of code", value: nf(TOTAL_LINES), sub: "in the tracked files" },
      { label: "Biggest file", value: nf(max(SRC_LINES)), sub: "lines in one file" },
      { label: "Test functions", value: nf(TEST_FUNCS_TOTAL), sub: "that guard them" },
    ],
  },
}

const PALETTE = {
  light: ["#ded9cd", "#bcb5a5", "#7a7466", "#ff3d00"],
  dark: ["#ded9cd", "#bcb5a5", "#7a7466", "#ff3d00"],
}

const PROOF: string[] = [
  "$ python schoolio/islands/mkdata.py",
  "commits       91",
  "churn         244013",
  "test files    164",
  "test funcs    4108",
  "source files  719",
  "total lines   208447",
  "",
  "$ git rev-list --count HEAD",
  "91",
]

function Bars({ values, dates, labels, unit, unitPlural }: {
  values: number[]; dates: string[]; labels?: string[]; unit: string; unitPlural: string
}) {
  const maxV = Math.max(...values, 1)
  const [hover, setHover] = React.useState<number | null>(null)
  const hot = values.indexOf(maxV)
  return (
    <div className="ms-bars">
      <div className="ms-bars__head">
        <span className="ms-bars__title">{values.length} bars, one per {unit}. Hover a bar for its number.</span>
        <span className="ms-bars__hover">
          {hover === null
            ? "\u2014"
            : `${dates[hover].slice(0, 10)} \u00b7 ${nf(values[hover])} ${values[hover] === 1 ? unit : unitPlural}` +
              (labels ? ` \u00b7 ${labels[hover]}` : "")}
        </span>
      </div>
      <div className="ms-bars__plot">
        {values.map((v, i) => (
          <div className="ms-bars__col" key={i}
               onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}>
            <div className="ms-bars__bar"
                 style={{ height: Math.max(2, (v / maxV) * 100) + "%" }}
                 data-hot={i === hot ? 1 : 0}
                 data-zero={v === 0 ? 1 : 0} />
          </div>
        ))}
      </div>
      <div className="ms-bars__axis">
        <span>{dates[0].slice(0, 10)}</span>
        <span>{nf(maxV)} {unitPlural}</span>
        <span>{dates[dates.length - 1].slice(0, 10)}</span>
      </div>
    </div>
  )
}

function Measurements() {
  const [key, setKey] = React.useState<Key>("commits")
  const set = SETS[key]

  return (
    <div className="ms-wrap">
      <div className="ms-tog" role="tablist" aria-label="What to plot">
        {(Object.keys(SETS) as Key[]).map((k) => (
          <button
            key={k}
            role="tab"
            aria-selected={k === key}
            className={"ms-tog__b" + (k === key ? " is-on" : "")}
            onClick={() => setKey(k)}
          >
            {SETS[k].tab}
          </button>
        ))}
      </div>

      <div className="ms-stats">
        {set.stats.map((s) => (
          <div className="ms-stat" key={s.label}>
            <span className="ms-stat__k">{s.label}</span>
            <span className="ms-stat__v">
              {s.value}
              {s.unit ? <span className="ms-stat__u"> {s.unit}</span> : null}
            </span>
            {s.sub ? <span className="ms-stat__s">{s.sub}</span> : null}
          </div>
        ))}
      </div>

      <div className="ms-sky">
        <Bars values={set.matrix} dates={set.dates} labels={set.labels}
              unit={set.unit} unitPlural={set.unitPlural} />
        <div className="ms-sky__foot">
          <span className="ms-sky__title">{set.title}</span>
          <span className="ms-sky__caption">{set.caption}</span>
        </div>
      </div>

      <div className="ms-proof">
        <div className="ms-proof__l">
          <p className="ms-h">How it was measured</p>
          <p className="ms-proof__p">
            One script reads the repository: git for the history, the files themselves for
            the sizes. It prints the numbers the cards show, and it regenerates the data behind
            the plot. Nothing here is a benchmark, and nothing here is about your results.
          </p>
        </div>
        <Terminal sequence={false} className="ms-termbox">
          {PROOF.map((line, i) => (
            <TypingAnimation
              key={i}
              duration={14}
              delay={i * 110}
              startOnView={false}
              className={line.startsWith("$") ? "ms-prompt" : line.startsWith("DONE") ? "ms-ok" : "ms-dim"}
            >
              {line || " "}
            </TypingAnimation>
          ))}
        </Terminal>
      </div>
    </div>
  )
}

const mount = document.getElementById("measureMount")
if (mount) createRoot(mount).render(<Measurements />)
