# docs/claude-code-workflow.md — Usando Claude Code para SiuChat

Este documento no explica qué es Claude Code en abstracto. Explica cómo usarlo **específicamente para este proyecto** respetando el flujo de diseño-primero que venimos aplicando.

---

## El flujo óptimo

```
Decisión de diseño → Chat con Claude.ai → Prompt en docs/ → Claude Code (Plan Mode) → Review diff → Accept → Commit
```

Cada paso tiene un propósito distinto. Saltear alguno genera los problemas típicos que el proyecto quiere evitar.

### 1. Decisión de diseño

Antes de abrir Claude Code, la pregunta "¿qué vamos a construir?" debe estar respondida. Si todavía no lo está, no abrás Claude Code — volvé al chat de Claude.ai.

**Señales de que todavía falta diseño:**
- Hay más de una forma razonable de hacer la cosa
- No está claro qué archivos se van a tocar
- No sabés qué validaciones correr al final para saber si funcionó

### 2. Chat con Claude.ai

En el chat se cierran las decisiones. No se escribe código (o mínimo, solo para ilustrar). El output del chat es un **prompt preparado** para Claude Code.

Los prompts de cada bloque se guardan en `docs/prompt-XXX.md` para que si la sesión se interrumpe, podés retomar sin tener que volver a diseñar.

### 3. Prompt en `docs/`

El prompt no es un chat conversacional, es una instrucción ejecutable con:
- Contexto (qué se hizo antes)
- Alcance exacto (qué archivos sí, qué archivos no)
- Decisiones ya tomadas (para que Claude Code no las abra)
- Reglas obligatorias (referencia a CLAUDE.md + específicas del prompt)
- Pasos concretos
- Validaciones al final

Ver `docs/prompt-a4b.md` como ejemplo.

### 4. Claude Code en Plan Mode

**Plan Mode es obligatorio** para tareas que tocan más de un archivo. Se activa con `Shift + Tab` hasta que la barra inferior diga "plan mode".

En Plan Mode, Claude Code:
- Lee archivos
- Explora el código
- Corre comandos de lectura (`ls`, `git status`, `grep`)
- Propone un plan escrito
- **NO edita nada hasta tu aprobación**

El plan es una lista numerada de pasos. Revisás, decís "seguí" o "ajustá esto y aquello".

### 5. Review diff

Cuando Claude Code empieza a editar, muestra diffs archivo por archivo. Cada diff hay que leerlo antes de aceptar.

**Cosas específicas que revisar en este proyecto:**

- **Queries sin filtro de tenant_id** → rechazar. Regla crítica del proyecto.
- **Timestamps sin timezone** → rechazar. `DateTime(timezone=True)` obligatorio.
- **`except Exception: pass`** → rechazar. Silencia errores, viola CLAUDE.md.
- **Queries N+1** → pedir que use eager loading (`joinedload`) si hay loop sobre relaciones.
- **Nombres autogenerados de constraints/FKs** → rechazar. Nombres explícitos con `name="..."`.
- **`.json()` sin verificar contenido** → rechazar. Regla documentada.
- **Hardcoding de IDs** (tenant, channel, etc.) → rechazar, es anti-multi-tenant.

**Bug común que compila pero está mal:** que use `datetime.utcnow()` en lugar de `datetime.now(timezone.utc)`. Lo primero es deprecated y devuelve naive datetime — rompe con columnas `TIMESTAMPTZ`.

### 6. Accept + Commit

Cuando aceptás todos los diffs de una tarea, Claude Code los aplica. Después vos hacés el commit (Claude Code no debería commitear automáticamente).

Mensaje de commit sugerido:
```
feat(fase4-a4b): refactor services/whatsapp.py para multi-tenant

- Resolución de channel por phone_number_id
- Find-or-create de contact con sync Zoho
- Find-or-create de conversation con tenant_id denormalizado
- Manejo de errores Zoho (mensaje se guarda igual)
- Idempotencia via whatsapp_message_id

Siguiendo CLAUDE.md y diseño validado en docs/prompt-a4b.md
```

---

## Decisiones que NO se delegan a Claude Code

Si Claude Code pregunta algo como:

- "¿Querés que use async o sync?"
- "¿Prefiero A o B como approach?"
- "¿Qué tipo de dato para esta columna?"
- "¿Dónde debería vivir esta función?"

**La respuesta nunca es "vos decidí".** Volvé al chat de Claude.ai, tomá la decisión con fundamento, y después le decís a Claude Code qué hacer.

Las decisiones tomadas "porque pareció razonable" son las que después hay que revertir con dolor.

---

## Cuándo es aceptable saltear el chat

Para tareas chicas y locales, se puede ir directo a Claude Code sin diseño previo en Claude.ai:

- Renombrar una variable
- Agregar un log
- Arreglar un typo
- Formatear código
- Agregar un docstring
- Extract method en una función larga
- Fix de un bug trivial (ej: off-by-one en un slice)

Regla de dedo: **si podés describirlo en una frase y es un cambio en un archivo, vas directo**. Si es más que eso, diseñá primero.

---

## Comandos de Claude Code que conviene recordar

| Comando | Uso |
|---|---|
| `Shift + Tab` | Cambiar entre modos (auto / plan / approval) |
| `/clear` | Limpiar el contexto de la sesión (empezás de cero) |
| `/compact` | Resumir la conversación actual sin perder el hilo |
| `/cost` | Ver uso de tokens/costo de la sesión actual |
| `/help` | Ver todos los comandos disponibles |
| `think hard` (en prompt) | Pedir que Claude piense más antes de actuar |
| `ultrathink` (en prompt) | Máximo thinking budget para problemas complejos |

---

## Cuándo usar `/clear`

Usar `/clear` cuando:
- Terminás una tarea y empezás otra distinta
- El contexto se llenó de debug irrelevante
- Cambiaste radicalmente de archivo o módulo

No usar cuando:
- Estás en el medio de un flujo multi-paso (perdés el hilo)
- Acabás de diseñar algo y vas a ejecutarlo ahora (el contexto del diseño sirve)

---

## Errores comunes al empezar con Claude Code

1. **Pedirle tareas demasiado grandes.** "Refactorizá todo para multi-tenant" es malo. "Refactorizá este archivo siguiendo este diseño" es bueno.

2. **Aceptar diffs sin leer.** El código compila ≠ el código está bien. Los bugs más caros son los que se ven razonables.

3. **Dejar que decida arquitectura sola.** Las decisiones de diseño las tomás vos (solo o con Claude.ai), no Claude Code.

4. **No commitear entre tareas.** Si haces A.4.b, commiteá antes de arrancar A.4.c. Si A.4.c rompe algo, podés volver al último commit en segundos.

5. **Usar el mismo contexto para múltiples tareas.** Después de terminar una tarea grande, `/clear` y empezá limpia.

---

## Debugging con Claude Code

Cuando algo falla:

1. **Pegale el error completo** (stack trace, logs, output) en el prompt. No resumas.
2. **Pedile que diagnostique antes de arreglar**. En Plan Mode, el plan debería explicar la causa raíz, no solo la solución.
3. **Validá que el fix es correcto** — no solo que "ya no tira error". A veces silenciar un error es peor que dejarlo fallar.

Si el error es misterioso y persiste:
- Volvé a Claude.ai con el error y un extracto del código
- Puede ser un bug de diseño, no de implementación
- Valida con test mínimo reproducible
