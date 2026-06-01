@ Arquivo fonte: teste3.txt
@ Gerado por: AnalisadorSemantico.py
@ ============================================
@ Codigo Assembly gerado - ARMv7 DEC1-SOC
@ ============================================

.section .data
.align 8
res1: .double 0.0
.align 8
res2: .double 0.0
.align 8
c3: .double 1.0
.align 8
c4: .double 2.0
.align 8
res5: .double 0.0
.align 8
c6: .double 1.5
.align 8
c7: .double 2.5
.align 8
res8: .double 0.0
.align 8
c9: .double 10.0
.align 8
c10: .double 3.0
.align 8
res11: .double 0.0
.align 8
c12: .double 8.0
.align 8
c13: .double 3.0
.align 8
res14: .double 0.0
.align 8
c15: .double 7.0
.align 8
c16: .double 2.0
.align 8
res17: .double 0.0
.align 8
c18: .double 7.0
.align 8
res19: .double 0.0
.align 8
res20: .double 0.0
.align 8
c21: .double 8.0
.align 8
c24: .double 1.0
.align 8
res25: .double 0.0
.align 8
res26: .double 0.0
.align 8
c27: .double 100.0
.align 8
v_BASE: .double 0.0
.align 8
res28: .double 0.0
.align 8
res29: .double 0.0
.align 8
res30: .double 0.0
.align 8
c31: .double 0.0
.align 8
v_ITER: .double 0.0
.align 8
res32: .double 0.0
.align 8
c33: .double 4.0
.align 8
res34: .double 0.0
.align 8
c35: .double 10.0
.align 8
res38: .double 0.0
.align 8
res39: .double 0.0
.align 8
c40: .double 50.0
.align 8
c43: .double 0.0
.align 8
res44: .double 0.0
.align 8
res47: .double 0.0
.align 8
res50: .double 0.0
.align 8
res53: .double 0.0
.align 8
res56: .double 0.0
.align 8
c57: .double 200.0
.align 8
res60: .double 0.0
.align 8
v_SINAL: .double 0.0
.align 8
res65: .double 0.0
.align 8
res70: .double 0.0
.align 8
c73: .double 5.0
.align 8
res76: .double 0.0
.align 8
res77: .double 0.0
.align 8
res78: .double 0.0
.align 8
v_TRUE: .double 0.0
.align 8
res79: .double 0.0
.align 8
v_FALSE: .double 0.0
.align 8
res80: .double 0.0

.section .text
.global _start
_start:
  @ ==== stmt #1 -> res1 ====
  @ --- START ---
  LDR R0, =res1
  VSTR D0, [R0]
  @ ==== stmt #2 -> res2 ====
  LDR R0, =c3
  VLDR D0, [R0]
  LDR R0, =c4
  VLDR D1, [R0]
  VADD.F64 D0, D0, D1
  LDR R0, =res2
  VSTR D0, [R0]
  @ ==== stmt #3 -> res5 ====
  LDR R0, =c6
  VLDR D0, [R0]
  LDR R0, =c7
  VLDR D1, [R0]
  VADD.F64 D0, D0, D1
  LDR R0, =res5
  VSTR D0, [R0]
  @ ==== stmt #4 -> res8 ====
  LDR R0, =c9
  VLDR D0, [R0]
  LDR R0, =c10
  VLDR D1, [R0]
  VSUB.F64 D0, D0, D1
  LDR R0, =res8
  VSTR D0, [R0]
  @ ==== stmt #5 -> res11 ====
  LDR R0, =c12
  VLDR D0, [R0]
  LDR R0, =c13
  VLDR D1, [R0]
  VMUL.F64 D0, D0, D1
  LDR R0, =res11
  VSTR D0, [R0]
  @ ==== stmt #6 -> res14 ====
  LDR R0, =c15
  VLDR D0, [R0]
  LDR R0, =c16
  VLDR D1, [R0]
  VDIV.F64 D0, D0, D1
  LDR R0, =res14
  VSTR D0, [R0]
  @ ==== stmt #7 -> res17 ====
  LDR R0, =c18
  VLDR D0, [R0]
  LDR R0, =c4
  VLDR D1, [R0]
  @ divisao inteira
  VCVT.S32.F64 S0, D0
  VCVT.S32.F64 S2, D1
  VMOV R0, S0
  VMOV R1, S2
  SDIV R0, R0, R1
  VMOV S0, R0
  VCVT.F64.S32 D0, S0
  LDR R0, =res17
  VSTR D0, [R0]
  @ ==== stmt #8 -> res19 ====
  LDR R0, =c18
  VLDR D0, [R0]
  LDR R0, =c4
  VLDR D1, [R0]
  @ modulo inteiro
  VCVT.S32.F64 S0, D0
  VCVT.S32.F64 S2, D1
  VMOV R0, S0
  VMOV R1, S2
  SDIV R2, R0, R1
  MUL R2, R2, R1
  SUB R0, R0, R2
  VMOV S0, R0
  VCVT.F64.S32 D0, S0
  LDR R0, =res19
  VSTR D0, [R0]
  @ ==== stmt #9 -> res20 ====
  LDR R0, =c4
  VLDR D0, [R0]
  LDR R0, =c21
  VLDR D1, [R0]
  @ potenciacao D0 ^ D1
  VMOV.F64 D2, D0
  VCVT.S32.F64 S0, D1
  VMOV R1, S0
  LDR R0, =c24
  VLDR D0, [R0]
pow_loop22:
  CMP R1, #0
  BEQ pow_end23
  VMUL.F64 D0, D0, D2
  SUB R1, R1, #1
  B pow_loop22
pow_end23:
  LDR R0, =res20
  VSTR D0, [R0]
  @ ==== stmt #10 -> res25 ====
  LDR R0, =c10
  VLDR D0, [R0]
  LDR R0, =c6
  VLDR D1, [R0]
  VADD.F64 D0, D0, D1
  LDR R0, =res25
  VSTR D0, [R0]
  @ ==== stmt #11 -> res26 ====
  LDR R0, =c27
  VLDR D0, [R0]
  @ STORE BASE
  LDR R0, =v_BASE
  VSTR D0, [R0]
  LDR R0, =res26
  VSTR D0, [R0]
  @ ==== stmt #12 -> res28 ====
  @ LOAD BASE
  LDR R0, =v_BASE
  VLDR D0, [R0]
  LDR R0, =res28
  VSTR D0, [R0]
  @ ==== stmt #13 -> res29 ====
  LDR R0, =c4
  VLDR D0, [R0]
  @ RES(2) <- res26
  LDR R0, =res26
  VLDR D0, [R0]
  LDR R0, =res29
  VSTR D0, [R0]
  @ ==== stmt #14 -> res30 ====
  LDR R0, =c31
  VLDR D0, [R0]
  @ STORE ITER
  LDR R0, =v_ITER
  VSTR D0, [R0]
  LDR R0, =res30
  VSTR D0, [R0]
  @ ==== stmt #15 -> res32 ====
  LDR R0, =c16
  VLDR D0, [R0]
  LDR R0, =c13
  VLDR D1, [R0]
  VADD.F64 D0, D0, D1
  LDR R0, =c33
  VLDR D1, [R0]
  VMUL.F64 D0, D0, D1
  LDR R0, =res32
  VSTR D0, [R0]
  @ ==== stmt #16 -> res34 ====
  LDR R0, =v_BASE
  VLDR D0, [R0]
  LDR R0, =c35
  VLDR D1, [R0]
  VSUB.F64 D0, D0, D1
  LDR R0, =c16
  VLDR D1, [R0]
  LDR R0, =c13
  VLDR D2, [R0]
  @ potenciacao D1 ^ D2
  VMOV.F64 D3, D1
  VCVT.S32.F64 S0, D2
  VMOV R1, S0
  LDR R0, =c24
  VLDR D1, [R0]
pow_loop36:
  CMP R1, #0
  BEQ pow_end37
  VMUL.F64 D1, D1, D3
  SUB R1, R1, #1
  B pow_loop36
pow_end37:
  VADD.F64 D0, D0, D1
  LDR R0, =res34
  VSTR D0, [R0]
  @ ==== stmt #17 -> res38 ====
  LDR R0, =c24
  VLDR D0, [R0]
  LDR R0, =c16
  VLDR D1, [R0]
  VADD.F64 D0, D0, D1
  LDR R0, =c13
  VLDR D1, [R0]
  LDR R0, =c33
  VLDR D2, [R0]
  VMUL.F64 D1, D1, D2
  VSUB.F64 D0, D0, D1
  LDR R0, =v_BASE
  VLDR D1, [R0]
  VDIV.F64 D0, D0, D1
  LDR R0, =res38
  VSTR D0, [R0]
  @ ==== stmt #18 -> res39 ====
  LDR R0, =v_BASE
  VLDR D0, [R0]
  LDR R0, =c40
  VLDR D1, [R0]
  VCMP.F64 D0, D1
  VMRS APSR_nzcv, FPSCR
  BGT cmp_t41
  LDR R0, =c43
  VLDR D0, [R0]
  B cmp_a42
cmp_t41:
  LDR R0, =c24
  VLDR D0, [R0]
cmp_a42:
  LDR R0, =res39
  VSTR D0, [R0]
  @ ==== stmt #19 -> res44 ====
  LDR R0, =v_ITER
  VLDR D0, [R0]
  LDR R0, =c9
  VLDR D1, [R0]
  VCMP.F64 D0, D1
  VMRS APSR_nzcv, FPSCR
  BLT cmp_t45
  LDR R0, =c43
  VLDR D0, [R0]
  B cmp_a46
cmp_t45:
  LDR R0, =c24
  VLDR D0, [R0]
cmp_a46:
  LDR R0, =res44
  VSTR D0, [R0]
  @ ==== stmt #20 -> res47 ====
  LDR R0, =v_BASE
  VLDR D0, [R0]
  LDR R0, =c27
  VLDR D1, [R0]
  VCMP.F64 D0, D1
  VMRS APSR_nzcv, FPSCR
  BEQ cmp_t48
  LDR R0, =c43
  VLDR D0, [R0]
  B cmp_a49
cmp_t48:
  LDR R0, =c24
  VLDR D0, [R0]
cmp_a49:
  LDR R0, =res47
  VSTR D0, [R0]
  @ ==== stmt #21 -> res50 ====
  LDR R0, =v_BASE
  VLDR D0, [R0]
  LDR R0, =c43
  VLDR D1, [R0]
  VCMP.F64 D0, D1
  VMRS APSR_nzcv, FPSCR
  BNE cmp_t51
  LDR R0, =c43
  VLDR D0, [R0]
  B cmp_a52
cmp_t51:
  LDR R0, =c24
  VLDR D0, [R0]
cmp_a52:
  LDR R0, =res50
  VSTR D0, [R0]
  @ ==== stmt #22 -> res53 ====
  LDR R0, =v_ITER
  VLDR D0, [R0]
  LDR R0, =c31
  VLDR D1, [R0]
  VCMP.F64 D0, D1
  VMRS APSR_nzcv, FPSCR
  BGE cmp_t54
  LDR R0, =c43
  VLDR D0, [R0]
  B cmp_a55
cmp_t54:
  LDR R0, =c24
  VLDR D0, [R0]
cmp_a55:
  LDR R0, =res53
  VSTR D0, [R0]
  @ ==== stmt #23 -> res56 ====
  LDR R0, =v_BASE
  VLDR D0, [R0]
  LDR R0, =c57
  VLDR D1, [R0]
  VCMP.F64 D0, D1
  VMRS APSR_nzcv, FPSCR
  BLE cmp_t58
  LDR R0, =c43
  VLDR D0, [R0]
  B cmp_a59
cmp_t58:
  LDR R0, =c24
  VLDR D0, [R0]
cmp_a59:
  LDR R0, =res56
  VSTR D0, [R0]
  @ ==== stmt #24 -> res60 ====
  @ --- IF: avalia condicao ---
  LDR R0, =v_BASE
  VLDR D0, [R0]
  LDR R0, =c43
  VLDR D1, [R0]
  VCMP.F64 D0, D1
  VMRS APSR_nzcv, FPSCR
  BGT cmp_t63
  LDR R0, =c43
  VLDR D0, [R0]
  B cmp_a64
cmp_t63:
  LDR R0, =c24
  VLDR D0, [R0]
cmp_a64:
  LDR R0, =c43
  VLDR D1, [R0]
  VCMP.F64 D0, D1
  VMRS APSR_nzcv, FPSCR
  BEQ else61
  @ ramo verdadeiro
  LDR R0, =c24
  VLDR D0, [R0]
  @ STORE SINAL
  LDR R0, =v_SINAL
  VSTR D0, [R0]
  B endif62
else61:
  @ ramo falso (else)
  LDR R0, =c43
  VLDR D0, [R0]
  @ STORE SINAL
  LDR R0, =v_SINAL
  VSTR D0, [R0]
endif62:
  LDR R0, =res60
  VSTR D0, [R0]
  @ ==== stmt #25 -> res65 ====
  @ --- IF: avalia condicao ---
  LDR R0, =v_ITER
  VLDR D0, [R0]
  LDR R0, =c31
  VLDR D1, [R0]
  VCMP.F64 D0, D1
  VMRS APSR_nzcv, FPSCR
  BEQ cmp_t68
  LDR R0, =c43
  VLDR D0, [R0]
  B cmp_a69
cmp_t68:
  LDR R0, =c24
  VLDR D0, [R0]
cmp_a69:
  LDR R0, =c43
  VLDR D1, [R0]
  VCMP.F64 D0, D1
  VMRS APSR_nzcv, FPSCR
  BEQ else66
  @ ramo verdadeiro
  LDR R0, =v_BASE
  VLDR D0, [R0]
  LDR R0, =c16
  VLDR D1, [R0]
  VMUL.F64 D0, D0, D1
  @ STORE BASE
  LDR R0, =v_BASE
  VSTR D0, [R0]
  B endif67
else66:
endif67:
  LDR R0, =res65
  VSTR D0, [R0]
  @ ==== stmt #26 -> res70 ====
  @ --- WHILE ---
while_loop71:
  LDR R0, =v_ITER
  VLDR D0, [R0]
  LDR R0, =c73
  VLDR D1, [R0]
  VCMP.F64 D0, D1
  VMRS APSR_nzcv, FPSCR
  BLT cmp_t74
  LDR R0, =c43
  VLDR D0, [R0]
  B cmp_a75
cmp_t74:
  LDR R0, =c24
  VLDR D0, [R0]
cmp_a75:
  LDR R0, =c43
  VLDR D1, [R0]
  VCMP.F64 D0, D1
  VMRS APSR_nzcv, FPSCR
  BEQ while_end72
  @ corpo do loop
  LDR R0, =v_ITER
  VLDR D0, [R0]
  LDR R0, =c3
  VLDR D1, [R0]
  VADD.F64 D0, D0, D1
  @ STORE ITER
  LDR R0, =v_ITER
  VSTR D0, [R0]
  B while_loop71
while_end72:
  LDR R0, =res70
  VSTR D0, [R0]
  @ ==== stmt #27 -> res76 ====
  @ LOAD ITER
  LDR R0, =v_ITER
  VLDR D0, [R0]
  LDR R0, =res76
  VSTR D0, [R0]
  @ ==== stmt #28 -> res77 ====
  LDR R0, =c3
  VLDR D0, [R0]
  @ RES(1) <- res76
  LDR R0, =res76
  VLDR D0, [R0]
  LDR R0, =res77
  VSTR D0, [R0]
  @ ==== stmt #29 -> res78 ====
  @ LOAD TRUE
  LDR R0, =v_TRUE
  VLDR D0, [R0]
  LDR R0, =res78
  VSTR D0, [R0]
  @ ==== stmt #30 -> res79 ====
  @ LOAD FALSE
  LDR R0, =v_FALSE
  VLDR D0, [R0]
  LDR R0, =res79
  VSTR D0, [R0]
  @ ==== stmt #31 -> res80 ====
  @ --- END ---
  LDR R0, =res80
  VSTR D0, [R0]

  @ fim do programa
  MOV R0, #0
  BX LR