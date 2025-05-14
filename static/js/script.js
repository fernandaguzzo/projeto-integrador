document.addEventListener('DOMContentLoaded', function() {
    // Verificar prazos de devolução
    function verificarPrazos() {
        const hoje = new Date();
        document.querySelectorAll('[data-devolucao]').forEach(item => {
            const dataDevolucao = new Date(item.getAttribute('data-devolucao'));
            if (dataDevolucao < hoje) {
                item.classList.add('atrasado');
            }
        });
    }
    verificarPrazos();

    // Confirmação para empréstimos e devoluções
    document.querySelectorAll('a[href*="/emprestar"], a[href*="/devolver"]').forEach(link => {
        link.addEventListener('click', function(e) {
            if (!confirm('Confirmar esta ação?')) {
                e.preventDefault();
            }
        });
    });
});