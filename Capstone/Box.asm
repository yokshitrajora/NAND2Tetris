// Box.asm  -  capstone project, K = 13
//
// While ANY key is pressed a black box is drawn; when the key is released
// the box disappears.
//
//   start row : K        = 13
//   height    : 20 rows
//   width     : 16 * ((K mod 4) + 1) = 16 * 2 = 32 pixels = 2 words
//
// One screen row = 32 words, so row 13 starts at SCREEN + 32*13
//                                              = 16384 + 416 = 16800.

(LOOP)                      // ---- 1. check the keyboard, pick the colour ----
    @KBD
    D=M
    @BLACK
    D;JNE                   // a key is down -> colour = black
    @color
    M=0                     // no key -> colour = white
    @DRAW
    0;JMP
(BLACK)
    @color
    M=-1                    // -1 = 1111111111111111 = 16 black pixels

(DRAW)                      // ---- 2. paint the box with that colour ----
    @16800                  // SCREEN + 32*13  (first word of row 13)
    D=A
    @addr
    M=D                     // addr = start of the current row
    @20                     // box height in rows
    D=A
    @rows
    M=D                     // rows = rows still to paint

(ROW)
    @2                      // box width in words (2 words = 32 pixels)
    D=A
    @cols
    M=D                     // cols = words still to paint in this row
    @addr
    D=M
    @p
    M=D                     // p = address of the word being painted

(COL)
    @color
    D=M
    @p
    A=M
    M=D                     // RAM[p] = colour  (paints 16 pixels)
    @p
    M=M+1                   // next word to the right
    @cols
    M=M-1
    D=M
    @COL
    D;JGT                   // more words in this row?

    @32
    D=A
    @addr
    M=D+M                   // addr += 32  -> same column, next row down
    @rows
    M=M-1
    D=M
    @ROW
    D;JGT                   // more rows?

    @LOOP
    0;JMP                   // all done -> look at the keyboard again
