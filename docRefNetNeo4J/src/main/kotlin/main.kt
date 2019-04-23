import com.google.gson.GsonBuilder
import com.google.gson.reflect.TypeToken
import github.etx.neo4j.DefaultNeoSerializer
import github.etx.neo4j.NeoLogging
import github.etx.neo4j.NeoQuery
import github.etx.neo4j.destruct
import org.neo4j.driver.v1.AuthTokens
import org.neo4j.driver.v1.Config
import org.neo4j.driver.v1.GraphDatabase
import org.slf4j.LoggerFactory
import java.io.File

fun main() {
    val gson = GsonBuilder().create()
    val json = File("../graph.json").readText()
    val documents = gson.fromJson<Map<String, Document>>(json, object:TypeToken<Map<String, Document>>(){}.type)

    val mentions = documents.values.flatMap {
            doc -> doc.mention_freq.entries.map { Triple(doc.name, it.key, it.value) }
    }

    val logger = LoggerFactory.getLogger(String::class.java)

    val driver = GraphDatabase.driver(
        "bolt://127.0.0.1",
        AuthTokens.basic("neo4j", "neo4j")
        , Config.build().withLogging(NeoLogging(logger)).toConfig()
    )
    val neo = NeoQuery(driver, DefaultNeoSerializer())
    println("Neo4J ready")

    repeat(10) {
        neo.submit("MATCH (n)\n" +
                "OPTIONAL MATCH (n)-[r]-()\n" +
                "WITH n,r LIMIT 50000\n" +
                "DELETE n,r\n" +
                "RETURN count(n) as deletedNodesCount")
    }
    neo.submit("MATCH ()-[r]-() DELETE r")
    neo.submit("MATCH (n) DELETE n")
    neo.submit("MATCH (n) OPTIONAL MATCH (n)-[r]-() DELETE n,r")
    neo.submit("MATCH (n), ()-[r]-() DELETE n,r")

    documents.values.withIndex().forEach {
        val ndx = it.index
        val it = it.value
        neo.submit("CREATE (d:Document {" +
                "name: {name}," +
                "type: {type}," +
                "doc_id: {doc_id}," +
                "pub_date: {pub_date}," +
                "monitored: {monitored}," +
                "in_force: {in_force}" +
                "})",
            it.destruct().filter { it.key != "mention_freq" })
        if (ndx%100==0)
            println("Adding node $ndx of ${documents.size}")
    }
    mentions.withIndex().forEach {
        val ndx = it.index
        val it = it.value
        neo.submit("MATCH (d1:Document),(d2:Document)\n" +
                "WHERE d1.name = {first} AND d2.name = {second}\n" +
                "CREATE (d1)-[m:MENTIONS{frequency: {third}}]->(d2)\n" +
                "RETURN m",
            it.destruct())
        if (ndx%100==0)
            println("Adding edge $ndx of ${mentions.size}")
    }

    println("Added ${documents.size} documents and ${mentions.size} mentions")

    driver.close()
}