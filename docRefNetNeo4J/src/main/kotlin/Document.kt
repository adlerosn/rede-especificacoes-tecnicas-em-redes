data class Document(
    val name: String,
    val type: String,
    val doc_id: String,
    val pub_date: String,
    val monitored: Boolean,
    val in_force: Boolean,
    val mention_freq: Map<String, Int>
)