.section .data
.align 8
res1: .double 0.0
.align 8
res2: .double 0.0
.align 8
c3: .double 3.14
.align 8
c4: .double 2.0
.align 8
res5: .double 0.0
.align 8
c6: .double 5.0
.align 8
c7: .double 3.0
.align 8
res8: .double 0.0
.align 8
c9: .double 4.0
.align 8
res10: .double 0.0
.align 8
c11: .double 10.0
.align 8
res12: .double 0.0
.align 8
c13: .double 7.0
.align 8
res14: .double 0.0
.align 8
res15: .double 0.0
.align 8
c16: .double 8.0
.align 8
c19: .double 1.0
.align 8
res20: .double 0.0
.align 8
c21: .double 10.5
.align 8
v_CONTADOR: .double 0.0
.align 8
res22: .double 0.0
.align 8
res23: .double 0.0
.align 8
c24: .double 5.0
.align 8
res25: .double 0.0
.align 8
res26: .double 0.0
.align 8
c29: .double 0.0
.align 8
c32: .double 20.0
.align 8
v_RESULTADO: .double 0.0
.align 8
res33: .double 0.0
.align 8
res38: .double 0.0

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
  VSUB.F64 D0, D0, D1
  LDR R0, =res5
  VSTR D0, [R0]
  @ ==== stmt #4 -> res8 ====
  LDR R0, =c9
  VLDR D0, [R0]
  LDR R0, =c4
  VLDR D1, [R0]
  VMUL.F64 D0, D0, D1
  LDR R0, =res8
  VSTR D0, [R0]
  @ ==== stmt #5 -> res10 ====
  LDR R0, =c11
  VLDR D0, [R0]
  LDR R0, =c7
  VLDR D1, [R0]
  VDIV.F64 D0, D0, D1
  LDR R0, =res10
  VSTR D0, [R0]
  @ ==== stmt #6 -> res12 ====
  LDR R0, =c13
  VLDR D0, [R0]
  LDR R0, =c7
  VLDR D1, [R0]
  @ divisao inteira
  VCVT.S32.F64 S0, D0
  VCVT.S32.F64 S2, D1
  VMOV R0, S0
  VMOV R1, S2
  SDIV R0, R0, R1
  VMOV S0, R0
  VCVT.F64.S32 D0, S0
  LDR R0, =res12
  VSTR D0, [R0]
  @ ==== stmt #7 -> res14 ====
  LDR R0, =c11
  VLDR D0, [R0]
  LDR R0, =c7
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
  LDR R0, =res14
  VSTR D0, [R0]
  @ ==== stmt #8 -> res15 ====
  LDR R0, =c4
  VLDR D0, [R0]
  LDR R0, =c16
  VLDR D1, [R0]
  @ potenciacao D0 ^ D1
  VMOV.F64 D2, D0
  VCVT.S32.F64 S0, D1
  VMOV R1, S0
  LDR R0, =c19
  VLDR D0, [R0]
pow_loop17:
  CMP R1, #0
  BEQ pow_end18
  VMUL.F64 D0, D0, D2
  SUB R1, R1, #1
  B pow_loop17
pow_end18:
  LDR R0, =res15
  VSTR D0, [R0]
  @ ==== stmt #9 -> res20 ====
  LDR R0, =c21
  VLDR D0, [R0]
  @ STORE CONTADOR
  LDR R0, =v_CONTADOR
  VSTR D0, [R0]
  LDR R0, =res20
  VSTR D0, [R0]
  @ ==== stmt #10 -> res22 ====
  @ LOAD CONTADOR
  LDR R0, =v_CONTADOR
  VLDR D0, [R0]
  LDR R0, =res22
  VSTR D0, [R0]
  @ ==== stmt #11 -> res23 ====
  LDR R0, =c24
  VLDR D0, [R0]
  @ RES(5) <- res12
  LDR R0, =res12
  VLDR D0, [R0]
  LDR R0, =res23
  VSTR D0, [R0]
  @ ==== stmt #12 -> res25 ====
  LDR R0, =c7
  VLDR D0, [R0]
  LDR R0, =c9
  VLDR D1, [R0]
  VMUL.F64 D0, D0, D1
  LDR R0, =c4
  VLDR D1, [R0]
  VADD.F64 D0, D0, D1
  LDR R0, =res25
  VSTR D0, [R0]
  @ ==== stmt #13 -> res26 ====
  @ --- IF: avalia condicao ---
  LDR R0, =v_CONTADOR
  VLDR D0, [R0]
  LDR R0, =c6
  VLDR D1, [R0]
  VCMP.F64 D0, D1
  VMRS APSR_nzcv, FPSCR
  BGT cmp_t30
  LDR R0, =c29
  VLDR D0, [R0]
  B cmp_a31
cmp_t30:
  LDR R0, =c19
  VLDR D0, [R0]
cmp_a31:
  LDR R0, =c29
  VLDR D1, [R0]
  VCMP.F64 D0, D1
  VMRS APSR_nzcv, FPSCR
  BEQ else27
  @ ramo verdadeiro
  LDR R0, =c32
  VLDR D0, [R0]
  @ STORE RESULTADO
  LDR R0, =v_RESULTADO
  VSTR D0, [R0]
  B endif28
else27:
  @ ramo falso (else)
  LDR R0, =c29
  VLDR D0, [R0]
  @ STORE RESULTADO
  LDR R0, =v_RESULTADO
  VSTR D0, [R0]
endif28:
  LDR R0, =res26
  VSTR D0, [R0]
  @ ==== stmt #14 -> res33 ====
  @ --- WHILE ---
while_loop34:
  LDR R0, =v_CONTADOR
  VLDR D0, [R0]
  LDR R0, =c11
  VLDR D1, [R0]
  VCMP.F64 D0, D1
  VMRS APSR_nzcv, FPSCR
  BLT cmp_t36
  LDR R0, =c29
  VLDR D0, [R0]
  B cmp_a37
cmp_t36:
  LDR R0, =c19
  VLDR D0, [R0]
cmp_a37:
  LDR R0, =c29
  VLDR D1, [R0]
  VCMP.F64 D0, D1
  VMRS APSR_nzcv, FPSCR
  BEQ while_end35
  @ corpo do loop
  LDR R0, =v_CONTADOR
  VLDR D0, [R0]
  LDR R0, =c19
  VLDR D1, [R0]
  VADD.F64 D0, D0, D1
  @ STORE CONTADOR
  LDR R0, =v_CONTADOR
  VSTR D0, [R0]
  B while_loop34
while_end35:
  LDR R0, =res33
  VSTR D0, [R0]
  @ ==== stmt #15 -> res38 ====
  @ --- END ---
  LDR R0, =res38
  VSTR D0, [R0]

  @ fim do programa
  MOV R0, #0
  BX LR