/** @babel */

import { CompositeDisposable } from 'atom'
import call from './proc'

export default {
  config: {
    pythonPaths: {
      type: 'string',
      default: '',
      title: 'Python Executable Paths',
      description:
        '\
Paths to python executable, must be semicolon separated. \
First takes precedence. \
$PROJECT_NAME is the current project name \
$PROJECT is the current project full path',
    },
    blackThenIsort: {
      type: 'boolean',
      default: false,
      title: 'Run black then isort instead of isort then black.',
    },
    onlyWhenAProjectConfigIsFound: {
      type: 'boolean',
      default: true,
      title: 'Format only if a configuration file is found (pyproject.toml).',
    },
    runOnSave: {
      type: 'boolean',
      default: true,
      title: 'Run black isort on file save',
    },
    debug: {
      type: 'boolean',
      default: false,
      title: 'Enable console debug output',
    },
  },

  debug(...args) {
    atom.config.get('python-black-isort.debug') && console.debug(...args)
  },

  activate() {
    this.subscriptions = new CompositeDisposable()
    this.subscriptions.add(
      atom.commands.add('atom-text-editor[data-grammar~=python]', {
        'python-black-isort:format': () =>
          atom.workspace.getActiveTextEditor() &&
          this.format(atom.workspace.getActiveTextEditor()),
      })
    )
    this.debug('Debug is on')
    this.subscriptions.add(
      atom.workspace.observeTextEditors(async editor => {
        if (
          !editor.getFileName() ||
          !editor.getFileName().endsWith('.py') ||
          !editor.getFileName().endsWith('.pyi')
        ) {
          return
        }
        this.subscriptions.add(
          editor.onDidSave(async () => {
            if (atom.config.get('python-black-isort.runOnSave')) {
              this.debug(editor.getFileName(), 'has been saved. Formatting')
              this.format(editor)
            }
          })
        )
      })
    )
  },

  deactivate() {
    this.subscriptions.dispose()
  },

  async format(editor) {
    try {
      const { file } = await call(
        {
          cmd: 'fix',
          source: editor.getBuffer().getText(),
          black_then_isort: atom.config.get(
            'python-black-isort.blackThenIsort'
          ),
        },
        editor
      )
      editor.getBuffer().setTextViaDiff(file)
      this.debug('Formated to', file)
    } catch (error) {
      console.error('Python Black Isort error:', error)
    }
    return true
  },
}
