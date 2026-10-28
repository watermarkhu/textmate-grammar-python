function total = nested_while_comments(limit)
%{
Top-level block comment before nested loops.
%{
Nested block comment content can contain code-looking text:
while false
    total = -1;
end
%}
The outer block remains active after the nested terminator.
%}

total = 0;
while total < limit
    inner = 0;
    while inner < 2
        total = total + 1;
        inner = inner + 1;
    end
end
end
