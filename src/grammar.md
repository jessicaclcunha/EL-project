Grammar   → 'start:' NonTerm NEWLINE RuleList

RuleList  → Rule RuleList 
        | Rule

Rule      → NonTerm '→' AltList NEWLINE

AltList   → Seq 
        | Seq '|' AltList

Seq       → Symbol Seq 
        | ε

Symbol    → NonTerm 
        | Term 
        | 'ε'

NonTerm   → IDENTIFIER
Term      → QUOTED_STRING