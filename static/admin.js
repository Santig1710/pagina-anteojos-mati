const adminData = window.adminData || { products: [], companies: [], brands: [] };
const productMap = new Map(adminData.products.map((product) => [String(product.id), product]));
const companyMap = new Map(adminData.companies.map((company) => [String(company.id), company]));
const brandMap = new Map(adminData.brands.map((brand) => [String(brand.id), brand]));

const productCompany = document.querySelector("#productCompany");
const productBrand = document.querySelector("#productBrand");
function filterProductBrands() {
  if (!productCompany || !productBrand) return;
  [...productBrand.options].forEach((option) => {
    option.hidden = Boolean(productCompany.value && option.value && option.dataset.company !== productCompany.value);
  });
  if (productBrand.selectedOptions[0]?.hidden) productBrand.value = "";
}
productCompany?.addEventListener("change", filterProductBrands);

document.querySelectorAll("[data-edit-product]").forEach((button) => {
  button.addEventListener("click", () => {
    const product = productMap.get(button.dataset.editProduct);
    if (!product) return;
    document.querySelector("#productId").value = product.id;
    document.querySelector("#productName").value = product.name;
    document.querySelector("#productCompany").value = product.company_id;
    filterProductBrands();
    document.querySelector("#productBrand").value = product.brand_id;
    document.querySelector("#productKind").value = product.kind;
    document.querySelector("#productPrice").value = product.price;
    document.querySelector("#productStock").value = product.stock;
    document.querySelector("#productDescription").value = product.description || "";
    document.querySelector("#productFeatured").checked = Boolean(product.featured);
    document.querySelector("#productFormTitle").textContent = `Editar anteojo #${product.id}`;
    document.querySelector("#productSubmit").innerHTML = 'Guardar cambios <span aria-hidden="true">↗</span>';
    document.querySelector("#cancelProductEdit").hidden = false;
    document.querySelector("#productEditor").scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

function resetProductForm() {
  const form = document.querySelector("#productForm");
  if (!form) return;
  form.reset();
  document.querySelector("#productId").value = "";
  document.querySelector("#productFormTitle").textContent = "Nuevo anteojo";
  document.querySelector("#productSubmit").innerHTML = 'Guardar anteojo <span aria-hidden="true">↗</span>';
  document.querySelector("#cancelProductEdit").hidden = true;
  filterProductBrands();
}
document.querySelector("#cancelProductEdit")?.addEventListener("click", resetProductForm);
document.querySelector("#newProductLink")?.addEventListener("click", resetProductForm);

document.querySelectorAll("[data-edit-company]").forEach((button) => {
  button.addEventListener("click", () => {
    const company = companyMap.get(button.dataset.editCompany);
    if (!company) return;
    document.querySelector("#companyId").value = company.id;
    document.querySelector("#companyName").value = company.name;
    document.querySelector("#companyDescription").value = company.description || "";
    document.querySelector("#companySubmit").innerHTML = 'Guardar cambios <span aria-hidden="true">↗</span>';
    document.querySelector("#cancelCompanyEdit").hidden = false;
    document.querySelector("#companyForm").scrollIntoView({ behavior: "smooth", block: "center" });
    document.querySelector("#companyName").focus();
  });
});
document.querySelector("#cancelCompanyEdit")?.addEventListener("click", () => {
  document.querySelector("#companyForm").reset();
  document.querySelector("#companyId").value = "";
  document.querySelector("#companySubmit").innerHTML = 'Agregar empresa <span aria-hidden="true">↗</span>';
  document.querySelector("#cancelCompanyEdit").hidden = true;
});

document.querySelectorAll("[data-edit-brand]").forEach((button) => {
  button.addEventListener("click", () => {
    const brand = brandMap.get(button.dataset.editBrand);
    if (!brand) return;
    document.querySelector("#brandId").value = brand.id;
    document.querySelector("#brandName").value = brand.name;
    document.querySelector("#brandCompany").value = brand.company_id;
    document.querySelector("#brandSubmit").innerHTML = 'Guardar cambios <span aria-hidden="true">↗</span>';
    document.querySelector("#cancelBrandEdit").hidden = false;
    document.querySelector("#brandForm").scrollIntoView({ behavior: "smooth", block: "center" });
    document.querySelector("#brandName").focus();
  });
});
document.querySelector("#cancelBrandEdit")?.addEventListener("click", () => {
  document.querySelector("#brandForm").reset();
  document.querySelector("#brandId").value = "";
  document.querySelector("#brandSubmit").innerHTML = 'Agregar marca <span aria-hidden="true">↗</span>';
  document.querySelector("#cancelBrandEdit").hidden = true;
});

document.querySelector("#adminProductSearch")?.addEventListener("input", (event) => {
  const query = event.target.value.trim().toLocaleLowerCase("es");
  document.querySelectorAll("[data-admin-search]").forEach((row) => {
    row.hidden = !row.dataset.adminSearch.includes(query);
  });
});

document.querySelectorAll(".order-entry").forEach((entry) => {
  entry.addEventListener("toggle", () => {
    if (entry.open) entry.querySelector("summary")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  });
});

filterProductBrands();