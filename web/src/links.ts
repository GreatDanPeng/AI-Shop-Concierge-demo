// The one kind of address the page follows from a reply: "#/store/<letters, digits, _ or ->", a store
// page of this shop. The router and the reply renderer both use this, so they cannot drift apart.
// Everything else (https://..., javascript:, //host, "..", a query string, another route) is not a
// store address, so a reply can never point the member anywhere else.
export const STORE_ADDRESS = /^#\/store\/([A-Za-z0-9_-]+)$/;

export const isStoreAddress = (address: string): boolean => STORE_ADDRESS.test(address);

export const storeIdOf = (address: string): string | null => STORE_ADDRESS.exec(address)?.[1] ?? null;

export const storeAddress = (id: string): string => `#/store/${id}`;
