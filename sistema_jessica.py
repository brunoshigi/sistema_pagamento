import os
from datetime import datetime
from decimal import Decimal
import json
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from dataclasses import dataclass
from typing import List, Dict, Optional

# Configurações básicas de fonte
FONT_TITLE = ("Arial", 20, "bold")
FONT_LABEL = ("Arial", 12)
FONT_ENTRY = ("Arial", 12)

class ConfigManager:
    def __init__(self):
        self.config = {'database.path': 'austral.db'}
    def get(self, key, default=None):
        return self.config.get(key, default)

@dataclass
class Venda:
    """
    Representa uma venda individual com todos os seus detalhes.
    """
    vendedor: str
    tipo_pagamento: str
    detalhes_pagamento: str
    bandeira: str
    valor: Decimal
    numero_boleta: str
    troca: bool
    data: str = None

    def __post_init__(self):
        if self.data is None:
            self.data = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.valor = Decimal(str(self.valor)).quantize(Decimal('0.01'))

    def to_dict(self) -> dict:
        return {
            'vendedor': self.vendedor,
            'tipo_pagamento': self.tipo_pagamento,
            'detalhes_pagamento': self.detalhes_pagamento,
            'bandeira': self.bandeira,
            'valor': str(self.valor),
            'numero_boleta': self.numero_boleta,
            'troca': self.troca,
            'data': self.data
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Venda':
        return cls(
            vendedor=data['vendedor'],
            tipo_pagamento=data['tipo_pagamento'],
            detalhes_pagamento=data['detalhes_pagamento'],
            bandeira=data['bandeira'],
            valor=Decimal(data['valor']),
            numero_boleta=data['numero_boleta'],
            troca=data['troca'],
            data=data['data']
        )

class SistemaCaixa:
    """Sistema de gerenciamento de vendas com interface gráfica"""

    VENDEDORES = ["João", "Maria", "Pedro", "Ana"]
    PAGAMENTOS_COMPLETOS = [
        "Dinheiro", "PIX", "Troca",
        "Visa - Débito", "Visa - Crédito",
        "Mastercard - Débito", "Mastercard - Crédito",
        "Elo - Débito", "Elo - Crédito",
        "American Express - Débito", "American Express - Crédito",
        "Hipercard - Débito", "Hipercard - Crédito"
    ]
    OBSERVACOES_OPCOES = [
        "PDV", "POS Rede", "POS PagSeguro",
        "POS Getnet", "Link Rede", "Outro"
    ]

    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title("Sistema de Caixa")
        self.master.geometry("900x600")
        self.config = ConfigManager()
        # Define arquivo de backup com base na data atual
        self.ARQUIVO_BACKUP = f"vendas_{datetime.now().strftime('%Y%m%d')}.json"
        self.vendas: List[Venda] = []
        self.carregar_vendas()  # Carrega vendas do arquivo do dia se existir

        self.selected_item = None
        self.selected_id = None

        self._criar_interface()
        self._configurar_atalhos()
        self.atualizar_resumo()

    def _criar_interface(self):
        self._criar_frame_principal()
        self._criar_campos_entrada()
        self._criar_botoes()
        self._criar_treeview()
        self._criar_resumo()
        self.vendedor_cb.focus_set()

    def _criar_frame_principal(self):
        self.main_frame = ctk.CTkFrame(self.master)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _criar_campos_entrada(self):
        frame_campos = ctk.CTkFrame(self.main_frame)
        frame_campos.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        campos = [
            ("Vendedor:", "vendedor_cb", self.VENDEDORES, False),
            ("Pagamento:", "pagamento_cb", self.PAGAMENTOS_COMPLETOS, False),
            ("Observações:", "observacoes_cb", self.OBSERVACOES_OPCOES, True),
            ("Valor:", "valor_entry", None, False),
            ("Nº Boleta/Recibo:", "boleta_entry", None, False)
        ]

        self.widgets_entrada = []

        for i, (label, var_name, values, editable) in enumerate(campos):
            if values is not None:
                widget = self._criar_combobox(frame_campos, label, var_name, values, i, editable)
            else:
                widget = self._criar_entry(frame_campos, label, var_name, i)
            self.widgets_entrada.append(widget)

        for idx, widget in enumerate(self.widgets_entrada[:-1]):
            widget.bind("<Return>", lambda e, nxt=self.widgets_entrada[idx+1]: nxt.focus_set())
        self.widgets_entrada[-1].bind("<Return>", lambda e: self.adicionar_venda())

        frame_campos.columnconfigure(1, weight=1)

    def _criar_combobox(self, parent, label: str, var_name: str, values: list, row: int, editable: bool):
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        cb = ctk.CTkOptionMenu(parent, values=values, state="normal")
        cb.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=2)
        if values:
            cb.set(values[0])
        setattr(self, var_name, cb)
        return cb

    def _criar_entry(self, parent, label: str, var_name: str, row: int):
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        entry = ctk.CTkEntry(parent)
        entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=2)
        setattr(self, var_name, entry)
        return entry

    def _criar_botoes(self):
        frame_botoes = ctk.CTkFrame(self.main_frame)
        frame_botoes.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        botoes = [
            ("Adicionar Venda (Alt+A)", self.adicionar_venda),
            ("Excluir Venda (Alt+E)", self.excluir_venda),
            ("Gerar Relatório (Alt+R)", self.gerar_relatorio)
        ]

        for texto, comando in botoes:
            btn = ctk.CTkButton(frame_botoes, text=texto, command=comando)
            btn.pack(side=tk.LEFT, padx=5)

    def _criar_treeview(self):
        frame_inferior = ttk.Frame(self.main_frame)
        frame_inferior.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        frame_vendas = ttk.Frame(frame_inferior)
        frame_vendas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        colunas = [
            ("Vendedor", 100), ("Tipo", 100), ("Detalhes", 150),
            ("Bandeira", 100), ("Valor", 100), ("Boleta", 100),
            ("Troca", 60), ("Data", 150)
        ]

        self.tree = ttk.Treeview(frame_vendas, columns=[col[0] for col in colunas], show='headings')

        for col, width in colunas:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor='center')

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(frame_vendas, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind('<<TreeviewSelect>>', self.on_select)
        self.tree.bind('<Double-1>', self.on_double_click)
        self.tree.bind('<Delete>', lambda e: self.excluir_venda())

    def _criar_resumo(self):
        frame_resumo = ctk.CTkFrame(self.main_frame)
        frame_resumo.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=10, pady=5)

        ctk.CTkLabel(frame_resumo, text="Resumo Geral:").pack(anchor=tk.NW)

        self.resumo_text = ctk.CTkTextbox(frame_resumo, width=300)
        self.resumo_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _configurar_atalhos(self):
        atalhos = {
            '<Alt-a>': self.adicionar_venda,
            '<Alt-e>': self.excluir_venda,
            '<Alt-r>': self.gerar_relatorio
        }
        for atalho, comando in atalhos.items():
            self.master.bind_all(atalho, lambda e, cmd=comando: cmd())

    def adicionar_venda(self):
        try:
            dados_venda = self._coletar_dados_venda()
            if not dados_venda:
                return

            venda = Venda(**dados_venda)
            self.vendas.append(venda)
            self._adicionar_venda_treeview(venda)
            self.atualizar_resumo()
            self.salvar_vendas()
            self.limpar_campos()

            messagebox.showinfo("Sucesso", "Venda registrada com sucesso!")
        except ValueError as e:
            messagebox.showerror("Erro", str(e))

    def _coletar_dados_venda(self) -> Optional[Dict]:
        vendedor = self.vendedor_cb.get()
        pagamento_escolhido = self.pagamento_cb.get()

        if not vendedor or not pagamento_escolhido:
            messagebox.showerror("Erro", "Selecione o vendedor e o tipo de pagamento.")
            return None

        try:
            valor = Decimal(self.valor_entry.get().replace(',', '.'))
            # Permitir valor zero para "Troca"
            if pagamento_escolhido != "Troca" and valor <= 0:
                raise ValueError
        except:
            if pagamento_escolhido == "Troca":
                # Para "Troca", se houver erro na conversão, assumimos valor zero
                valor = Decimal('0.00')
            else:
                messagebox.showerror("Erro", "Valor inválido. Digite um número válido maior que zero.")
                return None

        tipo_pagamento, bandeira, detalhes_pagamento, troca = self._processar_pagamento(pagamento_escolhido)

        numero_boleta = self.boleta_entry.get().strip()
        if not numero_boleta:
            messagebox.showerror("Erro", "Número da Boleta/Recibo é obrigatório.")
            return None

        return {
            'vendedor': vendedor,
            'tipo_pagamento': tipo_pagamento,
            'detalhes_pagamento': detalhes_pagamento or self.observacoes_cb.get(),
            'bandeira': bandeira,
            'valor': valor,
            'numero_boleta': numero_boleta,
            'troca': troca
        }

    def _processar_pagamento(self, pagamento_escolhido: str) -> tuple:
        if pagamento_escolhido == "Dinheiro":
            return "Dinheiro", "", "", False
        elif pagamento_escolhido == "PIX":
            return "PIX", "", "", False
        elif pagamento_escolhido == "Troca":
            return "Troca", "", "", True
        else:
            partes = pagamento_escolhido.split(" - ")
            if len(partes) == 2:
                return "Cartão", partes[0], partes[1], False
            else:
                return pagamento_escolhido, "", "", False

    def _adicionar_venda_treeview(self, venda: Venda):
        self.tree.insert('', tk.END, values=(
            venda.vendedor,
            venda.tipo_pagamento,
            venda.detalhes_pagamento,
            venda.bandeira,
            f"R$ {venda.valor:.2f}",
            venda.numero_boleta,
            "Sim" if venda.troca else "Não",
            venda.data
        ))

    def excluir_venda(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showerror("Erro", "Nenhuma venda selecionada para excluir.")
            return

        if messagebox.askyesno("Confirmação", "Deseja excluir a venda selecionada?"):
            index = self.tree.index(selected_item)
            self.tree.delete(selected_item)
            del self.vendas[index]
            self.atualizar_resumo()
            self.salvar_vendas()

    def limpar_campos(self):
        self.vendedor_cb.set(self.VENDEDORES[0])
        self.pagamento_cb.set(self.PAGAMENTOS_COMPLETOS[0])
        self.observacoes_cb.set(self.OBSERVACOES_OPCOES[0])
        self.valor_entry.delete(0, tk.END)
        self.boleta_entry.delete(0, tk.END)
        self.vendedor_cb.focus_set()

    def gerar_relatorio(self):
        if not self.vendas:
            messagebox.showinfo("Relatório", "Nenhuma venda registrada.")
            return

        relatorio_window = ctk.CTkToplevel(self.master)
        relatorio_window.title("Relatório Detalhado")
        relatorio_window.geometry("800x600")

        text_area = ctk.CTkTextbox(relatorio_window, wrap="word", font=FONT_ENTRY)
        text_area.pack(expand=True, fill='both', padx=10, pady=10)

        vendas_por_vendedor = self._agrupar_vendas_por_vendedor()
        self._gerar_conteudo_relatorio(text_area, vendas_por_vendedor)

        frame_botoes = ttk.Frame(relatorio_window)
        frame_botoes.pack(pady=5)

        ttk.Button(
            frame_botoes,
            text="Salvar Relatório",
            command=lambda: self._salvar_relatorio(text_area.get("1.0", tk.END))
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            frame_botoes,
            text="Fechar",
            command=relatorio_window.destroy
        ).pack(side=tk.LEFT, padx=5)

    def _agrupar_vendas_por_vendedor(self) -> Dict[str, List[Venda]]:
        vendas_por_vendedor = {}
        for venda in self.vendas:
            vendas_por_vendedor.setdefault(venda.vendedor, []).append(venda)
        return vendas_por_vendedor

    def _gerar_conteudo_relatorio(self, text_area: ctk.CTkTextbox, vendas_por_vendedor: Dict[str, List[Venda]]):
        for vendedor, lista_vendas in vendas_por_vendedor.items():
            text_area.insert(tk.END, f"\nVendedor: {vendedor}\n")
            text_area.insert(tk.END, "="*50 + "\n\n")

            total_vendas = Decimal('0.00')
            resumo_pagamentos = {}
            resumo_bandeiras = {}
            trocas = []

            text_area.insert(tk.END, "DETALHAMENTO DAS VENDAS:\n\n")
            for venda in lista_vendas:
                total_vendas += venda.valor
                self._atualizar_resumos(venda, resumo_pagamentos, resumo_bandeiras, trocas)
                self._inserir_detalhes_venda(text_area, venda)

            self._inserir_resumos(text_area, total_vendas, resumo_pagamentos, resumo_bandeiras, trocas)
            text_area.insert(tk.END, "\n" + "-"*50 + "\n")

    def _atualizar_resumos(self, venda: Venda, resumo_pagamentos: dict, resumo_bandeiras: dict, trocas: list):
        key_pagamento = venda.tipo_pagamento
        if venda.detalhes_pagamento and venda.tipo_pagamento not in ["Dinheiro", "PIX", "Troca"]:
            key_pagamento += f" - {venda.detalhes_pagamento}"

        resumo_pagamentos[key_pagamento] = resumo_pagamentos.get(key_pagamento, Decimal('0.00')) + venda.valor

        if venda.bandeira:
            resumo_bandeiras[venda.bandeira] = resumo_bandeiras.get(venda.bandeira, Decimal('0.00')) + venda.valor

        if venda.troca:
            trocas.append(venda)

    def _inserir_detalhes_venda(self, text_area: ctk.CTkTextbox, venda: Venda):
        text_area.insert(tk.END, f"Data/Hora: {venda.data}\n")
        text_area.insert(tk.END, f"Boleta Nº: {venda.numero_boleta}\n")
        text_area.insert(tk.END, f"Pagamento: {venda.tipo_pagamento}\n")
        
        if venda.detalhes_pagamento:
            text_area.insert(tk.END, f"Detalhes: {venda.detalhes_pagamento}\n")
        if venda.bandeira:
            text_area.insert(tk.END, f"Bandeira: {venda.bandeira}\n")
            
        text_area.insert(tk.END, f"Valor: R$ {venda.valor:.2f}\n")
        text_area.insert(tk.END, f"Troca: {'Sim' if venda.troca else 'Não'}\n\n")

    def _inserir_resumos(self, text_area: ctk.CTkTextbox, total_vendas: Decimal, 
                         resumo_pagamentos: dict, resumo_bandeiras: dict, trocas: list):
        text_area.insert(tk.END, f"\nTOTAL DE VENDAS: R$ {total_vendas:.2f}\n\n")
        
        text_area.insert(tk.END, "RESUMO POR TIPO DE PAGAMENTO:\n")
        for tipo, valor in sorted(resumo_pagamentos.items()):
            text_area.insert(tk.END, f"- {tipo}: R$ {valor:.2f}\n")

        if resumo_bandeiras:
            text_area.insert(tk.END, "\nRESUMO POR BANDEIRA:\n")
            for bandeira, valor in sorted(resumo_bandeiras.items()):
                text_area.insert(tk.END, f"- {bandeira}: R$ {valor:.2f}\n")

        if trocas:
            total_trocas = sum(troca.valor for troca in trocas)
            text_area.insert(tk.END, "\nTROCAS REALIZADAS:\n")
            for troca in trocas:
                text_area.insert(tk.END, f"- Boleta {troca.numero_boleta}: R$ {troca.valor:.2f}\n")
            text_area.insert(tk.END, f"\nTotal de Trocas: R$ {total_trocas:.2f}\n")

    def _salvar_relatorio(self, conteudo: str):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"relatorio_{timestamp}.txt"
            with open(nome_arquivo, "w", encoding="utf-8") as file:
                file.write(conteudo)
            messagebox.showinfo("Sucesso", f"Relatório salvo como '{nome_arquivo}'")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar relatório: {str(e)}")

    def atualizar_resumo(self):
        self.resumo_text.configure(state='normal')
        self.resumo_text.delete("1.0", tk.END)

        if not self.vendas:
            self.resumo_text.insert(tk.END, "Nenhuma venda registrada.\n")
            self.resumo_text.configure(state='disabled')
            return

        total_geral = Decimal('0.00')
        resumo_por_tipo = {}
        resumo_por_bandeira = {}
        trocas = []

        for venda in self.vendas:
            self._atualizar_resumos(venda, resumo_por_tipo, resumo_por_bandeira, trocas)
            total_geral += venda.valor

        self._inserir_resumo_geral(total_geral, resumo_por_tipo, resumo_por_bandeira, trocas)
        self.resumo_text.configure(state='disabled')

    def _inserir_resumo_geral(self, total_geral: Decimal, resumo_por_tipo: dict, 
                              resumo_por_bandeira: dict, trocas: list):
        self.resumo_text.insert(tk.END, f"Total Geral: R$ {total_geral:.2f}\n\n")
        
        self.resumo_text.insert(tk.END, "Por Tipo de Pagamento:\n")
        for tipo, valor in sorted(resumo_por_tipo.items()):
            self.resumo_text.insert(tk.END, f"- {tipo}: R$ {valor:.2f}\n")

        if resumo_por_bandeira:
            self.resumo_text.insert(tk.END, "\nPor Bandeira:\n")
            for bandeira, valor in sorted(resumo_por_bandeira.items()):
                self.resumo_text.insert(tk.END, f"- {bandeira}: R$ {valor:.2f}\n")

        if trocas:
            total_trocas = sum(troca.valor for troca in trocas)
            self.resumo_text.insert(tk.END, f"\nTotal de Trocas: R$ {total_trocas:.2f}\n")

    def carregar_vendas(self):
        """Carrega vendas salvas do arquivo de backup do dia atual, se existir"""
        try:
            if os.path.exists(self.ARQUIVO_BACKUP):
                with open(self.ARQUIVO_BACKUP, 'r', encoding='utf-8') as file:
                    dados = json.load(file)
                    self.vendas = [Venda.from_dict(venda_dict) for venda_dict in dados]
                    # Carregar vendas na Treeview
                    for venda in self.vendas:
                        self._adicionar_venda_treeview(venda)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar vendas: {str(e)}")

    def salvar_vendas(self):
        """Salva as vendas no arquivo de backup do dia atual"""
        try:
            dados = [venda.to_dict() for venda in self.vendas]
            with open(self.ARQUIVO_BACKUP, 'w', encoding='utf-8') as file:
                json.dump(dados, file, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar vendas: {str(e)}")

    def on_select(self, event):
        pass

    def on_double_click(self, event):
        pass

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    app = SistemaCaixa(root)
    root.mainloop()
