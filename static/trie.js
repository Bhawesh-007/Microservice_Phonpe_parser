class TrieNode {
    constructor() {
        this.children = {},
            this.isEndofWord = {},
            this.categoryId = null,
            this.originalName = null
    }
}
class Trie {
    constructor() {
        this.root = new TrieNode()
    }
    insert(word, categoryId) {
        let current = this.root;
        const lowerWord = word.toLowerCase();
        for (let i = 0; i < lowerWord.length; i++) {
            let char = lowerWord[i];
            if (!current.children[char]) {
                current.children[char] = new TrieNode();
            }
            current = current.children[char];
        }
        current.isEndOfWord = true;
        current.categoryId = categoryId;
        current.originalName = word;
    }
    _findAllWords(node, results) {
        if (node.isEndOfWord) {
            results.push({ id: node.categoryId, name: node.originalName });
        }
        for (let char in node.children) {
            this._findAllWords(node.children[char], results);
        }
    }
    searchPrefix(prefix) {
        let current = this.root;
        const lowerPrefix = prefix.toLowerCase();
        let results = [];

        for (let i = 0; i < lowerPrefix.length; i++) {
            let char = lowerPrefix[i];
            if (!current.children[char]) {
                return results; // Prefix not found
            }
            current = current.children[char];
        }

        this._findAllWords(current, results);
        return results;
    }

}
if (typeof window === 'undefined') {
    console.log("🧪 Running local Trie tests...");

    const testTrie = new Trie();

    // Simulate loading your categories
    testTrie.insert("Groceries", 4);
    testTrie.insert("Food and Dining", 1);
    testTrie.insert("Transport", 2);
    testTrie.insert("Personal Transfer", 8);

    console.log("Search 'gro':", testTrie.searchPrefix("gro"));
    // Expected: [ { id: 4, name: 'Groceries' } ]

    console.log("Search 'F':", testTrie.searchPrefix("F"));
    // Expected: [ { id: 1, name: 'Food and Dining' } ]

    console.log("Search 'x':", testTrie.searchPrefix("x"));
    // Expected: []
}