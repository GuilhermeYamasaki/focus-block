# Focus Block

App desktop em Python/Tkinter para Linux Mint e compatíveis.

## Recursos
- bloqueio por domínio/URL no `/etc/hosts`
- senha para remover itens ou desbloquear tudo
- aplicação com elevação via `pkexec`
- ícone e atalho `.desktop`
- backup automático de `/etc/hosts` em `/etc/hosts.focusblock.bak`

## Instalar
```bash
chmod +x install.sh
./install.sh
```

## Dependências
```bash
sudo apt install python3 python3-tk policykit-1
```

## Observações
- a senha do app fica em `~/.config/focusblock/config.json` com hash PBKDF2-SHA256
- a senha do app não substitui a senha de administrador do sistema
