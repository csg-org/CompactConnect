const disableForm: any = {
    beforeMount(el, binding) {
        if (binding.value) {
            const inputElements = el.elements;

            if (inputElements.length > 1) {
                inputElements.forEach((element) => element.setAttribute('disabled', ''));
            } else if (inputElements.length > 0) {
                inputElements[0].setAttribute('disabled', '');
            }
        }
    },
};

export default disableForm;
