import GlassFolder from "@/components/ui/glass-folder-cards"

export default function Demo() {
  return (
    <div className="min-h-screen bg-[#0d0d0f] p-10">
      <GlassFolder
        label="memory"
        meta="10 tools"
        tone="dark"
        art="ember"
        seed={11}
        files={[
          { name: "school_remember", art: "ember" },
          { name: "school_recall", art: "dusk" },
          { name: "school_learn", art: "glacier" },
          { name: "school_conflict", art: "verdant" },
        ]}
        action="suggest"
        hint="you can press the add button to give suggestions for other tools in this category"
        suggestions={[{ label: "school_confidence" }, { label: "school_search" }]}
        width={330}
      />
    </div>
  )
}
