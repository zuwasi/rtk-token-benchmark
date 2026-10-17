import type { PluginAPI } from '@ampcode/plugin'

export const description =
	'Routes shell commands through rtk (github.com/rtk-ai/rtk) so command output is compressed before the model reads it. Set RTK_AMP_DISABLE=1 to turn it off.'

// rtk rewrite exit codes: 0 and 3 print a rewrite, 1 means no rewrite,
// 2 means a deny rule matched (with a message only when an rtk pipeline rule denied it).
export default function (amp: PluginAPI) {
	let rewritten = 0
	let passed = 0

	amp.on('tool.call', async (event, ctx) => {
		if (process.env.RTK_AMP_DISABLE === '1') return { action: 'allow' }

		const shell = amp.helpers.shellCommandFromToolCall(event)
		if (!shell || !shell.command.trim()) return { action: 'allow' }
		if (/^\s*rtk(\.exe)?\s/.test(shell.command)) return { action: 'allow' }
		// rtk turns `python -m pytest` into `rtk pytest`, which runs the pytest launcher on PATH
		// instead of the module under the chosen interpreter. When the launcher belongs to a
		// different Python install, a working command starts failing, so keep `-m` runs as typed.
		if (/\bpython[0-9.]*(\.exe)?\s+-m\s/i.test(shell.command)) return { action: 'allow' }

		// Bash uses `cmd`, shell_command uses `command`; patch whichever key holds the command.
		const key = Object.keys(event.input).find((k) => event.input[k] === shell.command)
		if (!key) return { action: 'allow' }

		let res
		try {
			res = await ctx.$`rtk rewrite ${shell.command}`
		} catch (err) {
			ctx.logger.log('rtk not runnable, leaving command unchanged:', String(err))
			return { action: 'allow' }
		}

		const out = res.stdout.trim()
		if ((res.exitCode === 0 || res.exitCode === 3) && out && out !== shell.command) {
			rewritten++
			ctx.logger.log(`rtk rewrite: ${shell.command} -> ${out}`)
			return { action: 'modify', input: { ...event.input, [key]: out } }
		}
		if (res.exitCode === 2 && out) {
			return { action: 'reject-and-continue', message: out }
		}
		passed++
		return { action: 'allow' }
	})

	amp.registerCommand(
		'rtk-gain',
		{ title: 'show token savings', category: 'rtk', description: 'Show rtk token savings (rtk gain)' },
		async (ctx) => {
			const res = await amp.$`rtk gain`
			const head = res.stdout.split('\n').slice(0, 9).join('\n')
			await ctx.ui.notify(
				`rtk rewrote ${rewritten} commands this session (${passed} passed through).\n\n${head}`,
			)
		},
	)
}
